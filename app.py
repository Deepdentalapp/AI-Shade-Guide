import streamlit as st
import numpy as np
from PIL import Image
import cv2
from fpdf import FPDF
import os
from datetime import datetime

# ---------------------- Setup ----------------------
st.set_page_config(page_title="AffoDent Tooth Shade Matcher", layout="centered")
st.title("🦷 AffoDent Tooth Shade Matcher")

DATA_DIR = "patient_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------- Shade Guides ----------------------
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

# ---------------------- Utilities ----------------------

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
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(200, 10, f"Name: {name}", ln=True)
    pdf.cell(200, 10, f"Sex: {sex}", ln=True)
    pdf.cell(200, 10, f"Age: {age}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, "🦷 Detected Shades:", ln=True)
    for system, shade in results.items():
        pdf.cell(200, 10, f"• {system}: {shade}", ln=True)

    if manual_override:
        pdf.ln(5)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(200, 10, f"Manual Override: {manual_override}", ln=True)
        pdf.set_text_color(0, 0, 0)

    if image_path and os.path.exists(image_path):
        pdf.image(image_path, w=100)

    pdf_path = os.path.join(DATA_DIR, f"{name.replace(' ', '_')}_report.pdf")
    pdf.output(pdf_path)
    return pdf_path

def save_patient_data(name, data):
    records = load_patient_data()
    records = [r for r in records if r["name"] != name]
    records.insert(0, data)
    records = records[:10]
    with open(os.path.join(DATA_DIR, "records.txt"), "w") as f:
        for r in records:
            f.write(str(r) + "\n")

def load_patient_data():
    path = os.path.join(DATA_DIR, "records.txt")
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        lines = f.readlines()
        return [eval(line.strip()) for line in lines]

# ---------------------- Main App ----------------------

with st.form("form"):
    name = st.text_input("👤 Name")
    sex = st.selectbox("⚧ Sex", ["Male", "Female", "Other"])
    age = st.number_input("🎂 Age", min_value=0, max_value=120, step=1)
    uploaded_file = st.file_uploader("📤 Upload Tooth Photo", type=["jpg", "jpeg", "png"])
    selected_systems = st.multiselect("📘 Shade Systems to Use", list(shade_systems.keys()), default=list(shade_systems.keys()))
    manual_override = st.selectbox("✍️ Manual Override (optional)", ["None"] + [shade for system in shade_systems.values() for shade in system.keys()])
    submitted = st.form_submit_button("🔍 Submit")

if submitted and uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    center_rgb = tuple(img_array[h//2, w//2])  # Sample from center
    st.image(image, caption="Uploaded Image", use_column_width=True)
    st.markdown(f"🎯 Sampled RGB at center: `{center_rgb}`")

    results = {}
    for system_name in selected_systems:
        closest = find_closest_shade(center_rgb, shade_systems[system_name])
        results[system_name] = closest

    final_manual = manual_override if manual_override != "None" else None
    st.success("✅ Shade Matching Complete")
    for sys, shade in results.items():
        st.markdown(f"**{sys}** ➜ `{shade}`")
    if final_manual:
        st.info(f"✍️ Manual override selected: `{final_manual}`")

    # Save image
    img_path = os.path.join(DATA_DIR, f"{name.replace(' ', '_')}_image.jpg")
    image.save(img_path)

    # Save report
    pdf_path = generate_pdf(name, sex, age, results, img_path, final_manual)

    # Save data
    save_patient_data(name, {
        "name": name,
        "sex": sex,
        "age": age,
        "results": results,
        "manual": final_manual,
        "image_path": img_path,
        "pdf_path": pdf_path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    with open(pdf_path, "rb") as f:
        st.download_button("📄 Download PDF Report", f, file_name=os.path.basename(pdf_path))

# ---------------------- Search History ----------------------

st.markdown("## 📁 View Previous Reports")
records = load_patient_data()
search_query = st.text_input("🔍 Search by Name")
filtered = [r for r in records if search_query.lower() in r["name"].lower()]

for r in filtered:
    st.markdown(f"**{r['name']}** ({r['age']} yrs, {r['sex']}) - *{r['timestamp']}*")
    st.markdown(", ".join([f"{k}: {v}" for k, v in r["results"].items()]))
    if r["manual"]:
        st.markdown(f"✍️ Manual override: `{r['manual']}`")
    with open(r["pdf_path"], "rb") as f:
        st.download_button(f"📄 Download Report - {r['name']}", f, file_name=os.path.basename(r["pdf_path"]))
