from fastapi import APIRouter, UploadFile, File, Depends
from pydantic import BaseModel
from app.utils.file_handler import save_upload_file
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter()

class UploadResponse(BaseModel):
    filename: str
    message: str
    file_path: str

@router.post("/", response_model=UploadResponse)
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to securely upload an image.
    Requires authentication.
    """
    saved_path = save_upload_file(file)
    
    return {
        "filename": file.filename,
        "message": "File uploaded successfully",
        "file_path": saved_path
    }
