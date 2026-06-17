import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import os

st.set_page_config(page_title="LUDII Game Intelligence", page_icon="🏺", layout="wide")

st.markdown("""
<style>
.main-title { font-size: 2.5rem; text-align: center; color: #D4A574; }
.subtitle { text-align: center; color: #888; }
.stButton>button { width: 100%; background-color: #D4A574; color: black; font-weight: bold; }
.sidebar-stats { padding: 10px; background: #1E1E1E; border-radius: 8px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

API = "http://localhost:8000"

# ========== DONNÉES RÉELLES DE LA BASE ==========
SHAPES = ["square", "rectangle", "hex", "tri", "quadhex", "celtic", "rect"]
SHAPE_LABELS = {
    "square": "Carré", "rectangle": "Rectangle", "hex": "Hexagonal",
    "tri": "Triangulaire", "quadhex": "QuadHex", "celtic": "Celtique", "rect": "Rectangulaire"
}
REGIONS_DB = ["Northern Africa", "Western Asia", "Southern Europe", "Eastern Asia",
              "Northern Europe", "Southern Asia", "Western Europe", "Eastern Europe",
              "South America", "Central Asia", "Southeastern Asia", "Eastern Africa"]
PERIODS_DB = ["Ancient", "Early Medieval", "Medieval", "Late Medieval", "1500s", "1600s",
              "1700s", "1800s", "1900s", "2000s", "Modern"]
MATERIAUX = ["", "Bois", "Pierre", "Argile", "Ivoire", "Os", "Métal", "Terre cuite"]

# ========== FONCTIONS API ==========
@st.cache_data(ttl=30)
def ask_rag(question):
    try:
        resp = requests.get(f"{API}/api/v1/rag/ask", params={"question": question}, timeout=120)
        return resp.json() if resp.status_code == 200 else {"error": f"Erreur {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def identify_dims(cols, rows, pieces, tolerance):
    try:
        data = {
            "board_cols": cols if cols > 0 else None,
            "board_rows": rows if rows > 0 else None,
            "total_pieces": pieces if pieces > 0 else None,
            "tolerance": tolerance,
            "pieces": []
        }
        resp = requests.post(f"{API}/api/v1/identify_partial_board", json=data, timeout=120)
        return resp.json() if resp.status_code == 200 else {"error": f"Erreur {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def reconstruct_3d(cols, rows, pieces, tolerance, shape_key):
    """Appelle l'API de reconstruction 3D"""
    try:
        data = {
            "board_cols": cols if cols > 0 else None,
            "board_rows": rows if rows > 0 else None,
            "total_pieces": pieces if pieces > 0 else None,
            "tolerance": tolerance,
            "pieces": [],
            "shape": shape_key
        }
        resp = requests.post(f"{API}/api/v1/reconstruct_3d", json=data, timeout=120)
        return resp.json() if resp.status_code == 200 else {"error": f"Erreur {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def show_3d_viewer(glb_url):
    """Affiche un viewer 3D interactif"""
    if not glb_url:
        st.warning("Modèle 3D non disponible")
        return
    
    # Construire l'URL complète
    if glb_url.startswith("/"):
        full_url = f"{API}{glb_url}"
    else:
        full_url = glb_url
    
    html = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <model-viewer 
        src="{full_url}" 
        alt="Plateau 3D reconstitué" 
        auto-rotate 
        camera-controls 
        touch-action="pan-y"
        style="width:100%; height:450px; background:#1a1a1a; border-radius:10px;"
        exposure="1.2"
        shadow-intensity="0.8"
        environment-image="neutral"
    >
        <div slot="progress-bar" style="color:white;">Chargement du modèle 3D...</div>
    </model-viewer>
    """
    components.html(html, height=470)

# ========== SIDEBAR AVEC ANALYTICS ==========
with st.sidebar:
    st.markdown("## 🏺 LUDII")
    st.markdown("---")
    
    st.markdown("### 📊 Base de données")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("🎲 Jeux", "1 621")
        st.metric("📜 Règles", "3 337")
    with col_b:
        st.metric("🔍 Signatures", "470")
        st.metric("🌍 Régions", "28")
    
    st.markdown("---")
    
    st.markdown("### 🏗️ Types de plateaux")
    plateau_data = {"Carré": 359, "Rectangle": 96, "Hexagonal": 26, "Triangulaire": 1, "Celtique": 2}
    for name, count in plateau_data.items():
        st.progress(count / 359, text=f"{name}: {count}")
    
    st.markdown("---")
    
    st.markdown("### 📏 Top dimensions")
    for dim, count in [("8×8", 142), ("5×5", 60), ("9×9", 33), ("4×4", 26), ("7×7", 22)]:
        st.write(f"• {dim} — {count} jeux")
    
    st.markdown("---")
    
    st.markdown("### ♟️ Pièces courantes")
    for piece, count in [("marker", 123), ("knight", 100), ("pawn", 88), ("rook", 85), ("queen", 81)]:
        st.write(f"• {piece}: {count}")
    
    st.markdown("---")
    st.caption("🏺 LUDII © 2026")

# ========== TITRE ==========
st.markdown('<p class="main-title">🏺 LUDII Game Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Intelligence Artificielle pour l\'Archéologie Ludique</p>', unsafe_allow_html=True)

# ========== ONGLETS ==========
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Description", "🗺️ Lieu", "📏 Dimensions", "💬 Question", "📷 Image", "📊 Dashboard"
])

# ========== TAB 1 : DESCRIPTION ==========
with tab1:
    st.header("📝 Description de l'artefact")
    
    c1, c2 = st.columns(2)
    with c1:
        description = st.text_area("Description générale", 
            "Plateau en bois trouvé dans une tombe égyptienne ancienne. Cases gravées.", height=100)
        materiau = st.selectbox("Matériau", MATERIAUX)
        etat = st.selectbox("État de conservation", ["", "Complet", "Partiel (>50%)", "Fragment (25-50%)", "Très dégradé (<25%)"])
    with c2:
        forme_plateau = st.selectbox("Forme du plateau", [""] + [SHAPE_LABELS[s] for s in SHAPES])
        symboles = st.text_input("Symboles / Motifs", "Cases gravées, hiéroglyphes")
        pieces_presentes = st.radio("Pièces présentes ?", ["Non", "Oui, quelques-unes", "Oui, beaucoup"])
    
    c3, c4, c5 = st.columns(3)
    with c3: cols_est = st.number_input("Colonnes estimées", 0, 50, 0)
    with c4: rows_est = st.number_input("Rangées estimées", 0, 50, 0)
    with c5: pieces_nb = st.number_input("Nombre de pièces", 0, 100, 0)
    
    if st.button("🔍 Analyser l'artefact", key="btn1"):
        with st.spinner("Analyse en cours..."):
            q = f"{description} "
            if materiau: q += f"Matériau: {materiau}. "
            if forme_plateau: q += f"Forme: {forme_plateau}. "
            if symboles: q += f"Motifs: {symboles}. "
            if etat: q += f"État: {etat}. "
            if cols_est > 0: q += f"Plateau d'environ {cols_est}×{rows_est}. "
            if pieces_nb > 0: q += f"Environ {pieces_nb} pièces. "
            q += "Quel est ce jeu ? Origine, règles, période ?"
            
            result = ask_rag(q)
            if "answer" in result:
                st.success(result["answer"])
            else:
                st.error(result.get("error", "Erreur"))

# ========== TAB 2 : LIEU ==========
with tab2:
    st.header("🗺️ Lieu de découverte")
    
    c1, c2 = st.columns(2)
    with c1: region = st.selectbox("Région historique", [""] + REGIONS_DB)
    with c2: periode = st.selectbox("Période estimée", [""] + PERIODS_DB)
    lieu_precis = st.text_input("Lieu précis (optionnel)", "Vallée des Rois")
    
    if st.button("🔍 Analyser le lieu", key="btn2"):
        with st.spinner("Analyse..."):
            q = "Quels jeux anciens"
            if region: q += f" viennent de {region}"
            if periode: q += f" et datent de la période {periode}"
            if lieu_precis: q += f" (trouvés à {lieu_precis})"
            q += " ? Origine et histoire."
            result = ask_rag(q)
            if "answer" in result: st.success(result["answer"])
            else: st.error(result.get("error", "Erreur"))

# ========== TAB 3 : DIMENSIONS + 3D ==========
with tab3:
    st.header("📏 Dimensions & Reconstruction 3D")
    
    shape_key = st.selectbox("Forme du plateau", ["square", "rectangle", "hex", "tri", "celtic", "quadhex", "inconnu"],
                             format_func=lambda x: SHAPE_LABELS.get(x, x.capitalize()))
    
    c1, c2, c3 = st.columns(3)
    with c1: cols = st.number_input("Colonnes / Largeur", 0, 20, 8)
    with c2: rows = st.number_input("Rangées / Hauteur", 0, 20, 8)
    with c3: nb_pieces = st.number_input("Pièces détectées", 0, 100, 0)
    tolerance = st.slider("Tolérance (cases d'écart)", 0, 5, 1)
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🔍 Identifier", key="btn3"):
            with st.spinner("Recherche dans la base..."):
                dims = identify_dims(cols, rows, nb_pieces, tolerance)
                if "best_match" in dims:
                    st.success(f"**🏆 Meilleur match : {dims['best_match']}**")
                    if "candidates" in dims:
                        st.write("**Candidats :**")
                        for c in dims["candidates"][:8]:
                            d = c.get("actual_dimensions", ["?", "?"])
                            st.write(f"• **{c['game']}** ({d[0]}×{d[1]}) — {c.get('relevance', 0):.1f}")
                shape_fr = SHAPE_LABELS.get(shape_key, shape_key)
                q = f"Quel jeu a un plateau {shape_fr} de {cols}×{rows} ?"
                if nb_pieces > 0: q += f" Avec {nb_pieces} pièces."
                q += " Origine et règles ?"
                rag = ask_rag(q)
                if "answer" in rag:
                    st.markdown("---")
                    st.markdown("### 💬 Analyse RAG")
                    st.success(rag["answer"])
    
    with col_btn2:
        if st.button("🏗️ Reconstruire en 3D", key="btn3d"):
            with st.spinner("🏗️ Génération du modèle 3D..."):
                result = reconstruct_3d(cols, rows, nb_pieces, tolerance, shape_key)
                if "error" not in result:
                    st.success(f"**{result.get('game', 'Plateau')}** reconstitué en 3D !")
                    st.info(f"Dimensions : {result.get('dimensions', [cols, rows])}")
                    
                    st.markdown("### 🎮 Visualisation 3D interactive")
                    show_3d_viewer(result.get("model_3d", ""))
                else:
                    st.error(result.get("error", "Échec de la reconstruction"))

# ========== TAB 4 : QUESTION ==========
with tab4:
    st.header("💬 Question libre")
    st.markdown("**Exemples :** *Quels sont les plus anciens jeux de plateau ?* — *Explique-moi les règles du Senet*")
    question = st.text_area("Votre question", "Quels sont les plus anciens jeux de plateau connus ?")
    if st.button("🔍 Demander", key="btn4"):
        with st.spinner("Recherche..."):
            result = ask_rag(question)
            if "answer" in result: st.success(result["answer"])
            else: st.error(result.get("error", "Erreur"))

# ========== TAB 5 : IMAGE ==========
with tab5:
    st.header("📷 Upload Image")
    file = st.file_uploader("Photo du plateau", type=["jpg", "png", "jpeg"])
    if file: st.image(file, width=400)
    if st.button("🔍 Analyser l'image", key="btn5") and file:
        with st.spinner("Analyse YOLO..."):
            try:
                resp = requests.post(f"{API}/api/v1/detect_game_from_image", files={"file": file}, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"**Jeu identifié : {data.get('identified_game', 'Inconnu')}**")
                    st.json(data)
                else: st.error(f"Erreur {resp.status_code}")
            except Exception as e: st.error(str(e))

# ========== TAB 6 : DASHBOARD ==========
with tab6:
    st.header("📊 Dashboard Analytics")
    
    st.markdown("### 📈 Indicateurs Clés")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("🎲 Jeux", "1 621")
    with k2: st.metric("📜 Règles", "3 337")
    with k3: st.metric("🔍 Signatures", "470")
    with k4: st.metric("🌍 Régions", "28")
    with k5: st.metric("📅 Périodes", "13")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 🏗️ Types de Plateaux")
        df_plateau = pd.DataFrame({
            "Type": ["Carré", "Rectangle", "Hexagonal", "Triangulaire", "Celtique", "Autres"],
            "Nombre": [359, 96, 26, 1, 2, 2]
        })
        fig1 = px.pie(df_plateau, values="Nombre", names="Type", 
                       title="Distribution des types de plateaux",
                       color_discrete_sequence=px.colors.sequential.Brwnyl)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_right:
        st.markdown("### 📏 Top 10 Dimensions")
        df_dims = pd.DataFrame({
            "Dimensions": ["8×8", "5×5", "9×9", "4×4", "7×7", "3×3", "6×6", "10×10", "2×13", "12×12"],
            "Jeux": [142, 60, 33, 26, 22, 21, 18, 17, 14, 11]
        })
        fig2 = px.bar(df_dims, x="Dimensions", y="Jeux", 
                       title="Dimensions les plus fréquentes",
                       color="Jeux", color_continuous_scale="Brwnyl")
        st.plotly_chart(fig2, use_container_width=True)
    
    col_left2, col_right2 = st.columns(2)
    
    with col_left2:
        st.markdown("### ♟️ Top 10 Pièces")
        df_pieces = pd.DataFrame({
            "Pièce": ["marker", "knight", "pawn", "rook", "queen", "king", "disc", "bishop", "counter", "ball"],
            "Nombre": [123, 100, 88, 85, 81, 77, 68, 54, 27, 26]
        })
        fig3 = px.bar(df_pieces, x="Pièce", y="Nombre",
                       title="Pièces les plus courantes",
                       color="Nombre", color_continuous_scale="Brwnyl")
        st.plotly_chart(fig3, use_container_width=True)
    
    with col_right2:
        st.markdown("### 🌍 Top Régions")
        df_regions = pd.DataFrame({
            "Région": ["Southern Europe", "Western Europe", "Northern Africa", "Eastern Asia",
                       "Southern Asia", "Northern Europe", "Western Asia", "Southeastern Asia"],
            "Jeux": [350, 280, 180, 150, 130, 120, 110, 90]
        })
        fig4 = px.bar(df_regions, x="Région", y="Jeux",
                       title="Jeux par région",
                       color="Jeux", color_continuous_scale="Brwnyl")
        fig4.update_xaxes(tickangle=45)
        st.plotly_chart(fig4, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🛠️ Stack Technique")
    tech_col1, tech_col2, tech_col3, tech_col4, tech_col5 = st.columns(5)
    with tech_col1: st.markdown("**🧠 Neo4j**\nGraphe connaissances")
    with tech_col2: st.markdown("**⚡ FastAPI**\nAPI REST")
    with tech_col3: st.markdown("**👁️ YOLOv8**\nVision")
    with tech_col4: st.markdown("**🤖 Gemini**\nLLM")
    with tech_col5: st.markdown("**🎨 Streamlit**\nInterface")

# ========== FOOTER ==========
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Jeux", "1 621")
col2.metric("Signatures YOLO", "470")
col3.metric("Régions", "28")
col4.metric("Périodes", "13")
st.markdown("🏺 **LUDII Game Intelligence** | Neo4j + YOLO + Gemini + Streamlit | © 2026")