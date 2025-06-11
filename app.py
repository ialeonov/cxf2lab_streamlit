import matplotlib.pyplot as plt
import streamlit as st
import xml.etree.ElementTree as ET
from colormath.color_objects import SpectralColor, LabColor, sRGBColor, LCHabColor
from colormath.color_conversions import convert_color
import io

# Настройки страницы
st.set_page_config(page_title="CXF → CIE Lab", layout="wide")
st.title("🎨 CXF → CIE Lab Конвертер")

uploaded_file = st.file_uploader("Загрузите CXF-файл", type=["cxf"])

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

# Отображение результатов
if uploaded_file:
    data_dict, lab_dict, mode = parse_cxf(uploaded_file.read())
    results = convert_to_lab(data_dict, lab_dict, mode)

    st.markdown("### Результаты:")
    header_cols = st.columns([1, 4, 1, 1, 1, 1, 1])
    with header_cols[0]: st.markdown("**Цвет**")
    with header_cols[1]: st.markdown("**Название**")
    with header_cols[2]: st.markdown("**L**")
    with header_cols[3]: st.markdown("**a**")
    with header_cols[4]: st.markdown("**b**")
    with header_cols[5]: st.markdown("**C**")
    with header_cols[6]: st.markdown("**h°**")

    for name, lab, rgb, lch in results:
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 4, 1, 1, 1, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div style='display:flex; align-items:center; height:100%;'>
                <div style='width:36px; height:36px; background-color:rgb({rgb[0]},{rgb[1]},{rgb[2]}); border:1px solid #ccc;'></div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{name}</span>", unsafe_allow_html=True)

        with col3:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{lab.lab_l:.2f}</span>", unsafe_allow_html=True)

        with col4:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{lab.lab_a:.2f}</span>", unsafe_allow_html=True)

        with col5:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{lab.lab_b:.2f}</span>", unsafe_allow_html=True)

        with col6:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{lch.lch_c:.2f}</span>", unsafe_allow_html=True)

        with col7:
            st.markdown(f"<span style='font-size:1.1em; font-weight:500'>{lch.lch_h:.1f}°</span>", unsafe_allow_html=True)
else:
    st.info("Пожалуйста, загрузите CXF-файл для обработки.")

# === График LCH: круг насыщенности ===
if uploaded_file and results:
    import numpy as np

    st.markdown("### Цветовой круг (LCh)")

    fig = plt.figure(figsize=(4, 4))  # размер 400x400 px примерно
    ax = fig.add_subplot(111, polar=True)

    for name, lab, rgb, lch in results:
        theta = np.deg2rad(lch.lch_h)
        r = lch.lch_c
        ax.scatter(theta, r, color=np.array(rgb)/255, s=100, edgecolor='black', alpha=0.9)

    ax.set_theta_zero_location('E')  # 0° справа
    ax.set_theta_direction(-1)       # по часовой стрелке
    ax.set_rlabel_position(135)
    ax.set_title("Оттенки (h°) и насыщенность (C)", va='bottom', fontsize=12)
    ax.grid(True)

    st.pyplot(fig)


# Футер
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 0.9em; color: gray;'>"
    "Developed by <strong>Ivan Leonov</strong> · ialeonov@gmail.com · 2025"
    "</div>",
    unsafe_allow_html=True
)

