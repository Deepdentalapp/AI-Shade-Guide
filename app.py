import streamlit as st
import numpy as np
from PIL import Image
import cv2
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# --------------------------- Setup ---------------------------
st.set_page_config(page_title="AffoDent Shade Matcher", layout="centered")
st.title("🦷 AffoDent Tooth Shade Matcher")
st.markdown("Upload a **clear photo of the tooth**, draw a box around the tooth, and get the best matching shade.")

DATA_DIR = "patient_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------- Shade Systems ------------------------
vita_classical = {
    "A1": (255, 240, 220), "A2": (240, 224, 200), "A3": (225, 205, 185),
    "A3.5": (210, 190, 170), "B1": (250, 235, 210), "B2": (235, 215, 190),
    "C1": (220, 200, 180), "C2": (205, 185, 165), "D2": (200, 180, 160)
}

vita_3d_master = {
    "1M1": (255, 243, 224), "2M1": (246, 231, 209), "2M2": (235, 219, 198),
    "3M2": (225, 205, 185), "3R2.5": (210, 190, 170), "4M1": (200, 180, 160)
}

ivoclar_chromascop = {
    "100": (255, 240, 220), "200": (245, 225, 205), "300": (230, 210, 190),
    "400": (215, 195, 175), "500": (200, 180, 160)
}

shade_systems = {
    "Vita Classical": vita_classical,
    "Vita 3D-Master": vita_3d_master,
    "Ivoclar Chromascop": ivoclar_chromascop
}

# ---------------------- Helper Functions ----------------------
def rgb_to_lab(rgb):
    rgb_arr = np.uint8([[list(rgb)]])
    lab = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
    return lab[0][0]

def find_closest_shade(input_rgb, system_dict):
    input_lab = rgb_to_lab(input_rgb)
    closest, min_dist = None, float("inf")
    for shade, ref_rgb in system_dict.items():
        ref_lab = rgb_to_lab(ref_rgb)
        dist = np.linalg.norm(input_lab - ref_lab)
        if dist < min_dist:
            min_dist, closest = dist, shade
    return closest

def generate_pdf(name, sex, age, results, image_path, manual_override=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, "AffoDent Professional Dental Clinic", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Name: {name}", ln=True)
    pdf.cell(200, 10, f"Sex: {sex}", ln=True)
    pdf.cell(200, 10, f"Age: {age}", ln=True)
    pdf.cell(200, 10, f"Date: {datetime.today().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, "Detected Shades:", ln=True)
    for system, shade in results.items():
        pdf.cell(200, 10, f"• {system}: {shade}", ln=True)
    if manual_override:
        pdf.ln(5)
        pdf.cell(200, 10, f"Manual Override: {manual_override}", ln=True)
    if image_path and os.path.exists(image_path):
        pdf.image(image_path, w=100)
    pdf_path = os.path.join(DATA_DIR, f"{name.replace(' ', '_')}_report.pdf")
    pdf.output(pdf_path)
    return pdf_path

# ---------------------- State Setup ----------------------
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# ---------------------- Form ----------------------
with st.form("patient_form"):
    name = st.text_input("Patient Name")
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    age = st.number_input("Age", 1, 120, 25)
    uploaded_file = st.file_uploader("Upload a clear tooth image", type=["jpg", "jpeg", "png"])
    manual_override = st.text_input("Manual override shade (optional)")
    submitted = st.form_submit_button("Submit")

    if submitted and uploaded_file:
        st.session_state.image_bytes = uploaded_file.read()
        st.session_state.name = name
        st.session_state.sex =
