import streamlit as st
from PIL import Image
import numpy as np
import cv2
import json
import os
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="Tooth Shade Matcher - AffoDent", layout="centered")
st.title("🦷 AffoDent Professional Dental Clinic - Tooth Shade Matcher")

# JSON file to store last 10 patients
DB_FILE = "patients.json"

# Load patient records
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        patient_db = json.load(f)
else:
    patient_db = []

# --- Shade Systems ---
vita_shades = {
    "A1": (255, 240, 220), "A2": (240, 224, 200),
    "A3": (225, 205, 185), "A3.5": (210, 190, 170),
    "B1": (250, 235, 210), "B2": (235, 215, 190),
    "C1": (220, 200, 180), "C2": (205, 185, 165),
    "D2": (200, 180, 160)
}

vita3d_shades = {
    "1M1": (255, 245, 235), "2M2": (235, 220, 205),
    "3M3": (215, 200, 185), "4M1": (190, 180, 165)
}

ivoclar_shades = {
    "100": (255, 240, 230), "200": (235, 220, 205),
    "300": (220, 200, 180), "400": (205, 185, 165)
}

# ---- Functions ----
def rgb_to_lab(rgb):
    rgb_arr = np.uint8([[list(rgb)]])
    lab = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
    return lab[0][0]

def get_closest_shade_lab(input_rgb, shade_guide):
    input_lab = rgb_to_lab(input_rgb)
    closest = None
    min_dist = float("inf")
    for shade, ref_rgb in shade_guide.items():
        ref_lab = rgb_to_lab(ref_rgb)
        dist = np.linalg.norm(input_lab - ref_lab)
        if dist < min_dist:
            min_dist = dist
            closest = shade
    return closest

def get_average_rgb(image: Image.Image):
    img_array = np.array(image.convert("RGB"))
    avg_color = tuple(np.mean(img_array.reshape(-1, 3), axis=0).astype(int))
    return avg_color

def save_to_db(entry):
    patient_db.insert(0, entry)
    if len(patient_db) > 10:
        patient_db.pop()
    with open(DB_FILE, "w") as f:
        json.dump(patient_db, f, indent=2)

def generate_pdf(entry):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Tooth Shade Report - AffoDent", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    for key, value in entry.items():
        if key != "image_path":
            pdf.cell(0, 10, f"{key}: {value}", ln=True)

    if "image_path" in entry and os.path.exists(entry["image_path"]):
        pdf.image(entry["image_path"], x=60, y=pdf.get_y()+10, w=90)

    filename = f"{entry['Name'].replace(' ', '_')}_shade_report.pdf"
    pdf.output(filename)
    return filename

# ---- UI Form ----
with st.form("patient_form"):
    st.subheader("Patient Info")
    name = st.text_input("Patient Name")
    age = st.number_input("Age", min_value=1, max_value=120)
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    uploaded_image = st.file_uploader("Upload Tooth Photo", type=["jpg", "jpeg", "png"])
    selected_systems = st.multiselect("Shade Systems to Compare", ["Vita", "Vita 3D Master", "Ivoclar Chromascop"], default=["Vita"])

    manual_override = st.checkbox("Manual Override")
    override_shade = None
    if manual_override:
        override_system = st.selectbox("Manual Shade System", selected_systems)
        if override_system == "Vita":
            override_shade = st.selectbox("Select Manual Shade", list(vita_shades.keys()))
        elif override_system == "Vita 3D Master":
            override_shade = st.selectbox("Select Manual Shade", list(vita3d_shades.keys()))
        elif override_system == "Ivoclar Chromascop":
            override_shade = st.selectbox("Select Manual Shade", list(ivoclar_shades.keys()))

    submitted = st.form_submit_button("🔍 Analyze Shade")

# ---- Shade Detection ----
if submitted and uploaded_image and name:
    image = Image.open(uploaded_image)
    avg_rgb = get_average_rgb(image)

    result = {}
    if "Vita" in selected_systems:
        result["Vita"] = get_closest_shade_lab(avg_rgb, vita_shades)
    if "Vita 3D Master" in selected_systems:
        result["Vita 3D Master"] = get_closest_shade_lab(avg_rgb, vita3d_shades)
    if "Ivoclar Chromascop" in selected_systems:
        result["Ivoclar Chromascop"] = get_closest_shade_lab(avg_rgb, ivoclar_shades)

    final_entry = {
        "Name": name,
        "Age": age,
        "Sex": sex,
        "Detected RGB": str(avg_rgb),
        "Auto Result": str(result),
        "Manual Shade": override_shade if manual_override else "Not Used",
        "Manual System": override_system if manual_override else "None",
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    img_path = f"saved_{name.replace(' ', '_')}.jpg"
    image.save(img_path)
    final_entry["image_path"] = img_path

    save_to_db(final_entry)

    st.success("✅ Analysis Complete!")
    st.write("🟢 **Auto Detected Shades:**")
    for system, shade in result.items():
        st.markdown(f"- **{system}**: {shade}")
    if manual_override:
        st.write(f"✏️ **Manual Override**: {override_shade} ({override_system})")

    pdf_path = generate_pdf(final_entry)
    with open(pdf_path, "rb") as f:
        st.download_button("📄 Download PDF Report", f, file_name=pdf_path)

# ---- View Previous Reports ----
st.subheader("📁 View Past Reports")
search_name = st.text_input("Search by Patient Name")

if search_name:
    matches = [p for p in patient_db if search_name.lower() in p["Name"].lower()]
    for p in matches:
        st.markdown(f"### {p['Name']} ({p['Date']})")
        st.write(p)
        if "image_path" in p and os.path.exists(p["image_path"]):
            st.image(p["image_path"], caption="Tooth Photo", width=300)
else:
    st.info("Enter a name above to view previous reports.")
