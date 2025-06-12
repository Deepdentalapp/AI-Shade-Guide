import streamlit as st
import numpy as np
from PIL import Image
import cv2
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime
from fpdf import FPDF

# ----------------------------- Config & Setup -----------------------------
st.set_page_config(page_title="AffoDent Shade Matcher", layout="centered")
st.title("🦷 AffoDent Tooth Shade Matcher")
st.markdown("Upload a **clear photo of the tooth**, draw a box around the tooth, and we'll suggest the best matching shade.")

DATA_DIR = "patient_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ----------------------------- Shade Guides -----------------------------

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

# ----------------------------- Functions -----------------------------

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

    pdf.cell(200, 10, txt="AffoDent Professional Dental Clinic", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Name: {name}", ln=True)
    pdf.cell(200, 10, f"Sex: {sex}", ln=True)
    pdf.cell(200, 10, f"Age: {age}", ln=True)

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

#
# ----------------------------- Main UI -----------------------------

# Collect patient info
with st.form("patient_info_form"):
    name = st.text_input("Patient Name", "")
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    age = st.number_input("Age", min_value=1, max_value=120, step=1)
    uploaded_file = st.file_uploader("Upload a clear tooth photo", type=["jpg", "jpeg", "png"])
    submit = st.form_submit_button("Submit")

if submit and uploaded_file:
    try:
        image = Image.open(uploaded_file).convert("RGB")
        image_np = np.array(image)

        st.image(image, caption="Uploaded Image", use_column_width=True)

        # Canvas to draw ROI
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",
            stroke_width=2,
            stroke_color="red",
            background_image=image,
            update_streamlit=True,
            height=image.height,
            width=image.width,
            drawing_mode="rect",
            key="canvas",
        )

        if canvas_result.json_data and canvas_result.json_data["objects"]:
            # Take the first drawn rectangle
            obj = canvas_result.json_data["objects"][0]
            left = int(obj["left"])
            top = int(obj["top"])
            width = int(obj["width"])
            height = int(obj["height"])

            roi = image_np[top:top+height, left:left+width]
            avg_color = np.mean(roi.reshape(-1, 3), axis=0).astype(int)

            st.markdown(f"**Detected Average Color (RGB)**: {tuple(avg_color)}")

            results = {}
            for system_name, system_dict in shade_systems.items():
                closest_shade = find_closest_shade(avg_color, system_dict)
                results[system_name] = closest_shade

            st.markdown("### 📝 Shade Suggestions")
            for k, v in results.items():
                st.write(f"**{k}**: {v}")

            # Manual override option
            manual_override = st.text_input("Manual override shade (optional)")

            # Save the uploaded image
            img_path = os.path.join(DATA_DIR, f"{name.replace(' ', '_')}_image.png")
            image.save(img_path)

            # Generate and offer PDF report
            pdf_path = generate_pdf(name, sex, age, results, img_path, manual_override)
            with open(pdf_path, "rb") as f:
                st.download_button("📄 Download Shade Report PDF", f, file_name=os.path.basename(pdf_path))

        else:
            st.warning("Please draw a rectangle over the tooth.")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
