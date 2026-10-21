import io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from tesseract_api import app

client = TestClient(app)

def image_bytes(text='MedIntel OCR Test 12345'):
    image = Image.new('RGB', (700, 180), 'white')
    ImageDraw.Draw(image).text((24, 40), text, fill='black')
    buf = io.BytesIO(); image.save(buf, format='PNG')
    return buf.getvalue()

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_extract_image_returns_real_blocks_and_metadata():
    response = client.post('/ocr/extract', files={'file': ('test.png', image_bytes(), 'image/png')}, data={'preprocessing_mode': 'balanced', 'language': 'eng'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['text'].strip()
    assert body['page_count'] == 1
    assert body['source'] == 'Tesseract OCR'
    assert body['blocks']
    assert all(0 <= b['bbox']['x'] <= 1 and 0 <= b['bbox']['y'] <= 1 for b in body['blocks'])

def test_invalid_file_type_rejected():
    response = client.post('/ocr/extract', files={'file': ('test.exe', b'not an image', 'application/octet-stream')})
    assert response.status_code == 415

def test_region_validation():
    response = client.post('/ocr/extract-region', files={'file': ('test.png', image_bytes(), 'image/png')}, data={'x': .8, 'y': .2, 'width': .4, 'height': .2})
    assert response.status_code == 422

def test_correction_and_benchmark():
    corrected = client.post('/ocr/correct', json={'text': 'helo world', 'corrected_text': 'hello world'})
    assert corrected.status_code == 200 and corrected.json()['changed']
    benchmark = client.post('/ocr/benchmark', json={'reference_text': 'hello world', 'extracted_text': 'hello world'})
    assert benchmark.status_code == 200 and benchmark.json()['word_error_rate'] == 0

def test_share_expiry_and_revocation():
    created = client.post('/shares', json={'content': 'share me', 'format': 'txt', 'filename': 'example.txt', 'expires_in_hours': 1})
    assert created.status_code == 201, created.text
    body = created.json(); token = body['share_url'].rstrip('/').split('/')[-1]
    downloaded = client.get(f'/shares/{token}')
    assert downloaded.status_code == 200 and downloaded.content == b'share me'
    revoked = client.delete(f'/shares/{token}', headers={'X-Share-Revocation-Token': body['revoke_token']})
    assert revoked.status_code == 204
    assert client.get(f'/shares/{token}').status_code == 404

def test_region_extract_maps_boxes_to_source_coordinates():
    response = client.post('/ocr/extract-region', files={'file': ('test.png', image_bytes('Region OCR 456'), 'image/png')}, data={'x': .1, 'y': .1, 'width': .8, 'height': .7, 'preprocessing_mode': 'balanced', 'language': 'eng'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['region']['x'] == .1
    assert all(b['bbox']['x'] >= .1 and b['bbox']['y'] >= .1 for b in body['blocks'])

def test_multipage_pdf_ocr():
    import fitz
    doc = fitz.open()
    for phrase in ('First OCR page 100', 'Second OCR page 200'):
        page = doc.new_page(width=500, height=200)
        page.insert_text((40, 80), phrase, fontsize=22)
    payload = doc.tobytes(); doc.close()
    response = client.post('/ocr/extract', files={'file': ('multi.pdf', payload, 'application/pdf')}, data={'preprocessing_mode': 'balanced', 'language': 'eng'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['page_count'] == 2
    assert len(body['pages']) == 2
    assert 'First' in body['text'] and 'Second' in body['text']
