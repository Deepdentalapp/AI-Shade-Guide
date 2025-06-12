import streamlit as st
import numpy as np
import cv2
from PIL import Image
from datetime import datetime
import base64
import os
from fpdf import FPDF

# App config
st.set_page_config(page_title="AffoDent Tooth Shade Matcher", layout="centered")
st.title("🦷 AffoDent Professional Dental Clinic")
st.subheader("Tooth Shade Detection & PDF Report")

# Directories
os.makedirs("records", exist_ok=True)

# Define shade systems
shade_guides = {
    "Vita Classical": {
        "A1": (255, 240, 220),
        "A2": (240, 224, 200),
        "A3": (225, 205, 185),
        "A3.5": (210, 190, 170),
        "B1": (250, 235, 210),
        "B2": (235, 215, 190),
        "C1": (220, 200, 180),
        "C2": (205, 185, 165),
        "D2": (200, 180, 160),
    },
    "Vita 3D Master": {
        "1M1": (250, 240, 230),
        "2M2": (235, 220, 200),
        "3M3": (220, 200, 180),
        "4M2": (205, 185, 165),
        "5M3": (190, 170, 150),
    },
    "Ivoclar Chromascop": {
        "100": (255, 245, 230),
        "200": (240, 225, 210),
        "300": (225, 205, 185),
        "400": (210, 190, 170),
        "500": (195, 175, 155),
    }
}

# RGB → LAB converter
def rgb_to_lab(rgb):
    arr = np.uint8([[list(rgb)]])
    return cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)[0][0]

# Closest shade for all systems
def get_closest_shades(rgb_input):
    input_lab = rgb_to_lab(rgb_input)
    result = {}
    for system, shades in shade_guides.items():
        closest = None
        min_dist = float("inf")
        for name, ref_rgb in shades.items():
            ref_lab = rgb_to_lab(ref_rgb)
            dist = np.linalg.norm(input_lab - ref_lab)
            if dist < min_dist:
                min_dist = dist
                closest = name
        result[system] = closest
    return result

# Patient info
with st.form("shade_form"):
    name = st.text_input("Patient Name")
    age = st.number_input("Age", min_value=0, max_value=120, step=1)
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    uploaded_image = st.file_uploader("Upload Tooth Image", type=["jpg", "jpeg", "png"])
    manual_override = st.checkbox("Enter manual shade?")
    selected_manual = None
    if manual_override:
        selected_manual = st.text_input("Manual shade entry (e.g. A2, 3M2, 300)")
    submitted = st.form_submit_button("Generate Report")

if submitted and uploaded_image:
    image = Image.open(uploaded_image).convert("RGB")
    img_array = np.array(image)

    # Average RGB
    avg_rgb = tuple(np.mean(img_array.reshape(-1, 3), axis=0).astype(int))

    # Get closest matches
    shade_result = get_closest_shades(avg_rgb)

    # Prepare report
    st.success("✅ Report generated!")
    st.image(image, caption="Uploaded Tooth Image", use_column_width=True)
    st.markdown(f"**Average RGB**: {avg_rgb}")
    st.markdown("### Shade Match Results:")
    for system, shade in shade_result.items():
        st.markdown(f"🟢 {system}: **{shade}**")

    if selected_manual:
        st.markdown(f"✍️ Manual Shade: **{selected_manual}**")

    # Save PDF
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"records/{name}_{now}.pdf"

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "AffoDent Professional Dental Clinic", ln=1, align="C")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, "C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Patient Name: {name}", ln=1)
    pdf.cell(0, 10, f"Age: {age}", ln=1)
    pdf.cell(0, 10, f"Sex: {sex}", ln=1)
    pdf.cell(0, 10, f"Average RGB: {avg_rgb}", ln=1)
    pdf.cell(0, 10, "Shade Matches:", ln=1)
    for system, shade in shade_result.items():
        pdf.cell(0, 10, f" - {system}: {shade}", ln=1)
    if selected_manual:
        pdf.cell(0, 10, f"Manual Shade Entry: {selected_manual}", ln=1)

    # Save image temporarily
    temp_img = "temp_img.jpg"
    image.save(temp_img)
    pdf.image(temp_img, x=10, y=None, w=100)
    pdf.output(filename)
    os.remove(temp_img)

    with open(filename, "rb") as f:
        b64_pdf = base64.b64encode(f.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(filename)}">📥 Download Report PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

    # Store in memory (last 10 patients)
    if "records" not in st.session_state:
        st.session_state.records = []
    st.session_state.records.insert(0, {
        "name": name, "time": now, "file": filename
    })
    st.session_state.records = st.session_state.records[:10]

# Show search & past reports
st.markdown("---")
st.subheader("📁 Previous Patient Records")
if "records" in st.session_state:
    search_name = st.text_input("🔍 Search by name")
    for record in st.session_state.records:
        if search_name.lower() in record["name"].lower():
            st.markdown(f"**{record['name']}** ({record['time']})")
            with open(record["file"], "rb") as f:
                b64_pdf = base64.b64encode(f.read()).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(record["file"])}">📥 Download</a>'
                st.markdown(href, unsafe_allow_html=True)
