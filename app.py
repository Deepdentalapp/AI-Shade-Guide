import streamlit as st
import numpy as np
from PIL import Image
import cv2
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
import os
import datetime

st.set_page_config(page_title="Tooth Shade Matcher - AffoDent", layout="wide")
st.title("🦷 AffoDent Tooth Shade Matcher")
st.markdown("Upload a **clear photo of the tooth**, tap to sample color, and compare across multiple shade systems.")

# Directory to store patient reports
os.makedirs("patient_reports", exist_ok=True)

# Shade systems dictionary
shade_systems = {
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
        "1M1": (252, 239, 224),
        "2M1": (245, 225, 210),
        "2M2": (230, 210, 190),
        "3M2": (215, 190, 170),
        "4M1": (200, 175, 155),
    },
    "Ivoclar Chromascop": {
        "100": (255, 245, 230),
        "110": (245, 235, 220),
        "130": (235, 215, 200),
        "210": (225, 200, 180),
        "220": (215, 190, 170),
        "230": (205, 180, 160),
        "240": (195, 170, 150),
        "250": (185, 160, 140),
        "260": (175, 150, 130),
        "430": (160, 140, 120),
    }
}

# Convert RGB to Lab
def rgb_to_lab(rgb):
    rgb_arr = np.uint8([[list(rgb)]])
    lab = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
    return lab[0][0]

# Compare RGB to closest shade in each system
def get_closest_shades(input_rgb):
    input_lab = rgb_to_lab(input_rgb)
    closest_shades = {}
    for system, shades in shade_systems.items():
        min_dist = float("inf")
        best_match = None
        for shade, rgb in shades.items():
            dist = np.linalg.norm(input_lab - rgb_to_lab(rgb))
            if dist < min_dist:
                min_dist = dist
                best_match = shade
        closest_shades[system] = best_match
    return closest_shades

# Save report as PDF
def generate_pdf(name, age, sex, selected_rgb, closest_shades, manual_override, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="AffoDent Professional Dental Clinic", ln=True, align='C')
    pdf.cell(200, 10, txt="Tooth Shade Matching Report", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Name: {name}    Age: {age}    Sex: {sex}", ln=True)
    pdf.cell(200, 10, txt=f"Selected RGB: {selected_rgb}", ln=True)

    pdf.ln(5)
    for system, shade in closest_shades.items():
        pdf.cell(200, 10, txt=f"{system} Match: {shade}", ln=True)

    if manual_override:
        pdf.ln(5)
        pdf.cell(200, 10, txt=f"Manual Override: {manual_override}", ln=True)

    pdf.output(filename)

# Load history
def load_history():
    files = sorted(os.listdir("patient_reports"), reverse=True)[:10]
    return [f.replace(".pdf", "") for f in files]

# Sidebar
with st.sidebar:
    st.header("Patient Info")
    name = st.text_input("Name")
    age = st.text_input("Age")
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    manual_override = st.selectbox("Manual Shade Override (Optional)", ["None"] + 
        [f"{sys} - {shade}" for sys, shades in shade_systems.items() for shade in shades])
    st.markdown("---")
    st.subheader("📁 Past Reports")
    search_term = st.text_input("🔍 Search by name")
    history = load_history()
    for record in history:
        if search_term.lower() in record.lower():
            st.markdown(f"[📝 {record}](patient_reports/{record}.pdf)")

uploaded_image = st.file_uploader("📤 Upload Tooth Image", type=["jpg", "jpeg", "png"])

if uploaded_image:
    image = Image.open(uploaded_image).convert("RGB")
    img_array = np.array(image)

    st.markdown("### ✏️ Click on the tooth area to sample color")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=1,
        background_image=image,
        update_streamlit=True,
        height=image.height,
        width=image.width,
        drawing_mode="point",
        point_display_radius=5,
        key="canvas"
    )

    if canvas_result.json_data and canvas_result.json_data["objects"]:
        last_point = canvas_result.json_data["objects"][-1]
        x = int(last_point["left"])
        y = int(last_point["top"])

        if 0 <= x < img_array.shape[1] and 0 <= y < img_array.shape[0]:
            selected_rgb = tuple(int(c) for c in img_array[y, x])
            st.markdown(f"🎯 **Selected RGB:** {selected_rgb}")
            st.color_picker("Color Preview", "#%02x%02x%02x" % selected_rgb, label_visibility="collapsed")

            closest_shades = get_closest_shades(selected_rgb)
            st.markdown("### 🔎 Closest Matches:")
            for system, shade in closest_shades.items():
                st.success(f"✅ {system}: **{shade}**")

            if st.button("📄 Generate Report"):
                filename = f"patient_reports/{name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                generate_pdf(name, age, sex, selected_rgb, closest_shades,
                             None if manual_override == "None" else manual_override, filename)
                st.success(f"✅ Report saved as: {filename}")
                st.markdown(f"[📥 Download Report]({filename})")
    else:
        st.info("Click anywhere on the image to sample the tooth color.")
else:
    st.warning("Please upload an image to begin.")
