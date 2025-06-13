import streamlit as st
import xml.etree.ElementTree as ET
from colormath.color_objects import SpectralColor, LabColor, sRGBColor, LCHabColor
from colormath.color_conversions import convert_color
import matplotlib.pyplot as plt
import numpy as np
import io

# Ручный расчёт deltaE (CIE76)
def delta_e_simple(color1: LabColor, color2: LabColor):
    return np.sqrt(
        (color1.lab_l - color2.lab_l) ** 2 +
        (color1.lab_a - color2.lab_a) ** 2 +
        (color1.lab_b - color2.lab_b) ** 2
    )

# Настройки страницы
st.set_page_config(page_title="CXF → CIE Lab", layout="wide")
st.title("🎨 CXF → CIE Lab конвертер")

uploaded_files = st.file_uploader("Загрузите один или несколько CXF-файлов", type=["cxf"], accept_multiple_files=True)

# Парсинг CXF
def parse_cxf(file_content):
    ns = '{http://colorexchangeformat.com/CxF3-core}'
    tree = ET.parse(io.BytesIO(file_content))
    root = tree.getroot()
    objects = root.findall(f".//{ns}ObjectCollection")

    color_data = {}
    lab_data = {}
    spec_mode = None

    for oc in objects:
        for color in oc:
            name = color.attrib.get('Name', 'Unnamed')

            for spec in color.findall(f".//{ns}ReflectanceSpectrum"):
                spec_code = spec.get('ColorSpecification')
                if spec_code in ['CSM0D502', 'CS000']:
                    spec_mode = '1'
                    color_data[name] = spec.text
                elif 'M0D50' in spec_code or spec_code == 'CSeXact_Advanced009489M0-NPD50-2':
                    spec_mode = '2'
                    color_data[name] = spec.text

            lab_nodes = color.findall(f".//{ns}ColorCIELab")
            for lab in lab_nodes:
                try:
                    L = float(lab.find(f"{ns}L").text)
                    A = float(lab.find(f"{ns}A").text)
                    B = float(lab.find(f"{ns}B").text)
                    lab_data[name] = (L, A, B)
                except:
                    continue

    return color_data, lab_data, spec_mode

# Дополнение спектра
def pad_spectral_data(values, mode):
    if mode == '1':
        values = ['0.0'] * 6 + values + ['0.0'] * 13
    elif mode == '2':
        values = ['0.0'] * 4 + values + ['0.0'] * 10
    return [float(v) for v in values]

# Конвертация в LAB + RGB + LCH
def convert_to_lab(data_dict, lab_dict, mode):
    results = []
    all_keys = sorted(set(data_dict.keys()) | set(lab_dict.keys()))

    for name in all_keys:
        if name in lab_dict:
            lab = lab_dict[name]
        elif name in data_dict:
            values = pad_spectral_data(data_dict[name].strip().split(), mode)
            spectral = SpectralColor(*values)
            lab = convert_color(spectral, LabColor).get_value_tuple()
        else:
            continue

        lab_obj = LabColor(*lab)
        rgb_obj = convert_color(lab_obj, sRGBColor)
        lch_obj = convert_color(lab_obj, LCHabColor)

        rgb = (
            max(0, min(255, int(rgb_obj.clamped_rgb_r * 255))),
            max(0, min(255, int(rgb_obj.clamped_rgb_g * 255))),
            max(0, min(255, int(rgb_obj.clamped_rgb_b * 255))),
        )

        results.append((name, lab_obj, rgb, lch_obj))

    return results

if uploaded_files:
    all_results = {}

    for file in uploaded_files:
        data_dict, lab_dict, mode = parse_cxf(file.read())
        results = convert_to_lab(data_dict, lab_dict, mode)
        all_results[file.name] = results

    st.markdown("""
    <div style='background-color:#f9f9f9; padding:1rem; border:1px solid #ccc; border-radius:10px; margin-bottom:1rem;'>
        <h3 style='text-align:center; color:#444;'>🎨 Результаты по каждому файлу</h3>
    </div>
    """, unsafe_allow_html=True)

    for file_name, results in all_results.items():
        st.markdown(f"**Файл:** `{file_name}`")
        header_cols = st.columns([1, 4, 1, 1, 1, 1, 1])
        for label, col in zip(["Цвет", "Название", "L", "a", "b", "C", "h°"], header_cols):
            col.markdown(f"**{label}**")

        for name, lab, rgb, lch in results:
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 4, 1, 1, 1, 1, 1])
            with col1:
                st.markdown(f"""
                <div style='width:36px; height:36px; background-color:rgb({rgb[0]},{rgb[1]},{rgb[2]}); border:1px solid #ccc;'></div>
                """, unsafe_allow_html=True)
            with col2:
                col2.markdown(f"{name}")
            with col3:
                col3.markdown(f"{lab.lab_l:.2f}")
            with col4:
                col4.markdown(f"{lab.lab_a:.2f}")
            with col5:
                col5.markdown(f"{lab.lab_b:.2f}")
            with col6:
                col6.markdown(f"{lch.lch_c:.2f}")
            with col7:
                col7.markdown(f"{lch.lch_h:.1f}°")

    with st.expander("🌈 Показать цветовой круг (LCh)"):
        st.markdown("Отображение распределения всех цветов по цветовому кругу (Hue vs Chroma)")
        fig = plt.figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111, polar=True)

        for results in all_results.values():
            for name, _, rgb, lch in results:
                ax.scatter(np.deg2rad(lch.lch_h), lch.lch_c, color=np.array(rgb)/255, s=40)

        ax.set_rticks([20, 40, 60, 80, 100])
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        st.pyplot(fig, use_container_width=False)

    with st.expander("🎯 Ввести координаты цвета для сравнения (ΔE)"):
        input_L = st.number_input("L*", min_value=0.0, max_value=100.0, value=50.0)
        input_a = st.number_input("a*", min_value=-128.0, max_value=128.0, value=0.0)
        input_b = st.number_input("b*", min_value=-128.0, max_value=128.0, value=0.0)
        user_lab = LabColor(lab_l=input_L, lab_a=input_a, lab_b=input_b)

        st.markdown("### ΔE между введённым цветом и каждым цветом из CXF:")
        for file_name, results in all_results.items():
            st.markdown(f"**Файл:** `{file_name}`")
            for name, lab, _, _ in results:
                delta = delta_e_simple(user_lab, lab)
                st.markdown(f"• <strong>{name}</strong>: ΔE = {delta:.2f}", unsafe_allow_html=True)

# Футер
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 0.9em; color: gray;'>"
    "Developed by <strong>Ivan Leonov</strong> · ialeonov@gmail.com · 2025"
    "</div>",
    unsafe_allow_html=True
)
