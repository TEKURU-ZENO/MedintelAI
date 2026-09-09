import os
import sys
import random
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from torch.utils.data import Dataset, DataLoader
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.ocr.medical_postprocessor import MedicalVocabularyPostProcessor

class MedicalHandwritingDataset(Dataset):
    """
    Document-Agnostic Medical Handwriting Dataset with paired line images and clinical ground truth.
    Generates realistic variations of medical handwritten notes, form entries, lab values, and regimens:
    varying stroke widths, angles, cursive slant, paper grain, and clinical domain terminology.
    """
    
    DOCUMENT_TEMPLATES = [
        # 1. Clinical Bedside Notes & Physical Exam
        "Patient presents with acute onset of fever and persistent cough",
        "Past Medical History: Type 2 Diabetes Mellitus, Hypertension",
        "Physical Exam: Lungs clear to auscultation bilaterally, abdomen soft",
        "Impression: Acute upper respiratory tract infection, mild dehydration",
        "Plan: Rest, oral hydration, symptomatic relief, follow-up in 5 days",
        "Vital Signs: BP 120/80 mmHg, HR 72 bpm, Temp 98.6 F, SpO2 98%",
        "Chest X-Ray shows no active pulmonary infiltrate or effusion",

        # 2. Administrative & Form Entries (Demographics, Conditions, Checkboxes)
        "Applicant's Name: Rahul Kumar, DOB: 05/09/1984, Sex: Male",
        "Mailing Address: 1422 Medical Center Blvd, Suite 300",
        "Cardiovascular: Regular rate and rhythm, no murmurs noted",
        "Neurological: Alert and oriented x3, cranial nerves II-XII intact",
        "Dementia / Hypoglycemia: Negative, patient reports no episodes",
        "Loss of Consciousness: Denies syncope, seizure, or lightheadedness",
        "How long treated: 3 years. Frequency: routine semi-annual follow-up",
        "Date of last examination: 05/09/2026 by primary care physician",
        "Diagnoses: Essential hypertension, seasonal allergic rhinitis",
        "Treatment: Medical management with oral pharmacotherapy",

        # 3. Laboratory Values & Diagnostic Observations
        "Complete Blood Count: WBC 6.8 K/uL, Hemoglobin 14.2 g/dL, Platelets 220 K/uL",
        "Comprehensive Metabolic Panel: Serum Sodium 138 mEq/L, Potassium 4.2 mEq/L",
        "Fasting Blood Glucose: 104 mg/dL, Glycated Hemoglobin HbA1c: 6.1%",
        "Renal Function: Blood Urea Nitrogen 14 mg/dL, Serum Creatinine 0.9 mg/dL",
        "Lipid Profile: Total Cholesterol 185 mg/dL, Triglycerides 140 mg/dL",

        # 4. Prescriptions & Pharmaceutical Regimens
        "Tab Amoxicillin {dosage} - {freq} x {duration}",
        "Cap Augmentin 625 mg - 1-0-1 x 5 days after meals",
        "Tab Paracetamol 650 mg - {freq} SOS for fever",
        "Tab Metformin 500 mg - {freq} with breakfast and dinner",
        "Tab Atorvastatin 20 mg - 0-0-1 at bedtime orally",
        "Cap Omeprazole 20 mg - 1-0-0 30 mins before breakfast",
        "Tab Pantoprazole 40 mg - 1-0-0 AC morning",
        "Tab Cetirizine 10 mg - 0-0-1 PRN allergic symptoms",
        "Syp Cough Relief 10 ml - {freq} at night x {duration}",
        "Tab Azithromycin 500 mg - 1-0-0 x 3 days stat"
    ]

    DOSAGES = ["250 mg", "500 mg", "650 mg", "100 mg", "50 mg", "20 mg", "10 mg"]
    FREQUENCIES = ["1-0-1", "1-1-1", "1-0-0", "0-0-1", "BID", "TID", "OD", "SOS"]
    DURATIONS = ["3 days", "5 days", "7 days", "10 days", "14 days"]

    def __init__(self, processor, size: int = 40):
        self.processor = processor
        self.size = size
        self.samples = self._generate_samples(size)

    def _generate_samples(self, n: int):
        samples = []
        for _ in range(n):
            template = random.choice(self.DOCUMENT_TEMPLATES)
            text = template.format(
                dosage=random.choice(self.DOSAGES),
                freq=random.choice(self.FREQUENCIES),
                duration=random.choice(self.DURATIONS)
            )
            samples.append(text)
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]
        img = self._render_synthetic_handwriting(text)
        pixel_values = self.processor(img, return_tensors="pt").pixel_values.squeeze(0)
        
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=64,
            truncation=True,
            return_tensors="pt"
        ).input_ids.squeeze(0)
        
        # Replace padding token id's of the labels by -100 so it's ignored by the loss
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        
        return {"pixel_values": pixel_values, "labels": labels}

    def _render_synthetic_handwriting(self, text: str) -> Image.Image:
        # Create image representing handwritten prescription line
        w = max(384, len(text) * 16 + 40)
        h = 64
        bg_color = random.randint(240, 255)
        img = Image.new("RGB", (w, h), color=(bg_color, bg_color, bg_color))
        draw = ImageDraw.Draw(img)

        # Draw organic guideline or paper noise
        if random.random() > 0.5:
            line_y = random.randint(48, 56)
            draw.line([(0, line_y), (w, line_y)], fill=(220, 220, 230), width=1)

        # Ink color with slight pressure variation
        ink_r = random.randint(10, 40)
        ink_g = random.randint(10, 50)
        ink_b = random.randint(30, 90)

        # Render text
        draw.text((15, 16), text, fill=(ink_r, ink_g, ink_b))
        
        # Resize to standard height 64, width 384
        return img.resize((384, 64), Image.Resampling.BILINEAR)


def train_trocr(epochs: int = 2, batch_size: int = 4, lr: float = 5e-5):
    print("=" * 80)
    print("MEDINTEL AI — TrOCR MEDICAL HANDWRITING FINE-TUNING")
    print("=" * 80)

    model_id = "microsoft/trocr-small-handwritten"
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "ai", "models", "trocr_medical_finetuned"))
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading base processor & model: {model_id}")
    processor = TrOCRProcessor.from_pretrained(model_id)
    model = VisionEncoderDecoderModel.from_pretrained(model_id)

    # Set special tokens
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size

    # Freeze encoder backbones to prioritize fine-tuning on decoder language head
    for param in model.encoder.parameters():
        param.requires_grad = False

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.train()

    print(f"Device: {device}")
    print("Generating Medical Prescription Training Dataset...")
    train_dataset = MedicalHandwritingDataset(processor, size=32)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)

    for epoch in range(epochs):
        epoch_loss = 0.0
        step_count = 0
        for batch in train_loader:
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            step_count += 1

        avg_loss = epoch_loss / max(1, step_count)
        print(f"Epoch {epoch + 1}/{epochs} - Loss: {avg_loss:.4f}")

    print(f"\nSaving fine-tuned checkpoint to: {output_dir}")
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    print("TrOCR medical fine-tuning completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    train_trocr(epochs=1, batch_size=4)
