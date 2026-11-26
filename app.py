"""PlaneaTambo – Frontend (Streamlit). Ejecutar: streamlit run app.py"""
import os

import streamlit as st
from dotenv import load_dotenv

import ai_service as ai
import db
import exporter

load_dotenv()
st.set_page_config(page_title="PlaneaTambo", page_icon="📘", layout="wide")
db.init_db()
ss = st.session_state

TIPOS = {"plan": "Plan de clase", "taller": "Taller", "evaluacion": "Evaluación"}
DESCR = {
    "plan": "Secuencia por sesiones alineada al currículo.",
    "taller": "Actividades con instrucciones claras para el aula.",
    "evaluacion": "Preguntas por competencia y nivel.",
}
GRADOS = db.GRADOS
PERIODOS = [f"Periodo {i}" for i in range(1, 5)]
PAGES = ["Inicio", "Mis materiales", "Contexto curricular", "Uso seguro de IA"]
OTRO = "Otro (escribir)…"

st.markdown(
    """<style>
[data-testid="stSidebar"]{background:#14352F}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] summary,[data-testid="stSidebar"] label{color:#fff!important}
[data-testid="stSidebar"] button{background:transparent;border:none;color:#fff;justify-content:flex-start}
[data-testid="stSidebar"] button p{color:#fff!important}
[data-testid="stSidebar"] button[kind="primary"],[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]{background:#1F5A50}
.warn{background:#FFF4DC;border:1px solid #F1D9A0;border-radius:8px;padding:.6rem .8rem;font-size:.9rem}
.step{color:#0F766E;font-size:.8rem;font-weight:600;margin-bottom:-.5rem}
</style>""",
    unsafe_allow_html=True,
)

# ---------- Estado ----------
for k, v in dict(page="Inicio", tipo=None, step=2, draft=None, draft_id=None, params={}, edit=False, coord=False).items():
    ss.setdefault(k, v)


def go(page):
    ss.page = page


def start(tipo):
    ss.update(tipo=tipo, page="Nuevo", step=2, draft=None, draft_id=None, edit=False)


def open_material(mid):
    m = db.get_material(mid)
    ss.update(tipo=m["tipo"], draft=m["content"], draft_id=mid, params=m["params"], step=3, edit=False, page="Nuevo")
    ss["_reset_checks"] = True


def reset_checks():
    ss["_reset_checks"] = True


def ctx_for(grado):
    c = db.get_curriculum(grado)
    return {"competencias": c["competencias"], "ejemplos": c["ejemplos"]}


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("# PlaneaTambo")
    for p in PAGES:
        active = ss.page == p or (p == "Inicio" and ss.page == "Nuevo")
        st.button(p, key=f"nav_{p}", on_click=go, args=(p,), use_container_width=True,
                  type="primary" if active else "secondary")
    st.write("")
    if not ai.has_api_key():
        st.caption("🧪 Modo demo: sin API key de Grok")
    with st.expander("Soy coordinador"):
        pin = st.text_input("PIN", type="password", key="pin")
        ss.coord = bool(pin) and pin == os.getenv("COORDINATOR_PIN", "1234")
        if ss.coord:
            st.caption("Puedes editar el contexto curricular.")
    st.caption("I.E. Politécnico Francisco de Paula Santander · El Tambo, Cauca")


# ---------- Páginas ----------
def page_inicio():
    st.title("Buen día, profe")
    st.caption("Inglés · Básica primaria y secundaria. ¿Qué quiere preparar hoy?")
    cols = st.columns(3)
    for col, (k, label) in zip(cols, TIPOS.items()):
        with col, st.container(border=True):
            st.subheader(label)
            st.caption(DESCR[k])
            st.button("Empezar", key=f"start_{k}", on_click=start, args=(k,), type="primary" if k == "plan" else "secondary")
    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        st.subheader("Materiales recientes")
        recent = db.list_materials(limit=5)
        if not recent:
            st.caption("Aún no has creado materiales.")
        for m in recent:
            a, b = st.columns([3, 1])
            a.write(f"{TIPOS[m['tipo']]} · {m['tema']} · {m['grado']}")
            b.caption(m["estado"])
    with right:
        st.markdown(
            '<div class="warn"><b>Antes de usar la IA</b><br>La IA puede inventar datos (alucinaciones). '
            "Todo material se revisa antes de exportarse. No escriba nombres ni datos personales de estudiantes.</div>",
            unsafe_allow_html=True,
        )
        st.button("Ver guía de uso seguro", on_click=go, args=("Uso seguro de IA",))


def page_nuevo():
    if not ss.tipo:
        st.title("Nuevo material")
        st.caption("Paso 1 de 3 · Elige el tipo de material")
        cols = st.columns(3)
        for col, (k, label) in zip(cols, TIPOS.items()):
            with col, st.container(border=True):
                st.subheader(label)
                st.caption(DESCR[k])
                st.button("Elegir", key=f"pick_{k}", on_click=start, args=(k,))
        return
    if ss.step == 3 and ss.draft:
        return page_revision()
    page_formulario()


def page_formulario():
    st.markdown('<div class="step">Paso 2 de 3 · Datos de la clase</div>', unsafe_allow_html=True)
    st.title(f"Nuevo {TIPOS[ss.tipo].lower()} de inglés")
    st.progress(2 / 3)
    form, summ = st.columns([2, 1])
    with form, st.container(border=True):
        a, b = st.columns(2)
        grado = a.selectbox("Grado", GRADOS, index=5, key="f_grado")
        periodo = b.selectbox("Periodo académico", PERIODOS, index=3, key="f_periodo")
        cur = db.get_curriculum(grado)
        temas = cur["temas"][periodo[-1]]

        a, b = st.columns(2)
        with a:
            sel = st.selectbox("Tema o unidad", temas + [OTRO] if temas else [OTRO], key="f_tema_sel")
            tema = st.text_input("Escribe el tema", key="f_tema_txt", placeholder="Ej.: Present Simple: daily routines") if sel == OTRO else sel
        with b:
            sel = st.selectbox("Competencia del currículo", cur["competencias"] + [OTRO] if cur["competencias"] else [OTRO], key="f_comp_sel")
            comp = st.text_input("Escribe la competencia", key="f_comp_txt", placeholder="Ej.: Comprensión de lectura") if sel == OTRO else sel

        a, b = st.columns(2)
        sesiones = a.selectbox("Número de sesiones", [1, 2, 3, 4, 5], index=1, key="f_ses")
        minutos = b.number_input("Duración por sesión (min)", 30, 120, 55, step=5, key="f_min")
        contexto = st.text_input("Contexto local (opcional)", key="f_ctx", placeholder="Ej.: usar lugares y actividades de El Tambo")
        adaptar = st.checkbox("Adaptar ejemplos al contexto de El Tambo, Cauca", value=True, key="f_adapt")
    with summ:
        with st.container(border=True):
            st.subheader("Resumen")
            st.caption(f"{TIPOS[ss.tipo]} · {grado} · {periodo}")
            st.caption(tema or "—")
            st.caption(f"{sesiones} sesiones de {minutos} min")
        st.markdown('<div class="warn">Privacidad: no incluya nombres, documentos ni datos de estudiantes en ningún campo.</div>',
                    unsafe_allow_html=True)

    a, _, b = st.columns([1, 4, 1.4])
    a.button("Atrás", on_click=go, args=("Inicio",))
    if b.button("Generar borrador", type="primary"):
        if not (tema or "").strip() or not (comp or "").strip():
            return st.error("Completa el tema y la competencia.")
        found = ai.check_privacy(f"{tema} {comp} {contexto}")
        if found:
            return st.error(f"Detectamos {found}. Quítalo antes de continuar: no se deben enviar datos personales a la IA.")
        params = dict(tipo_label=TIPOS[ss.tipo], grado=grado, periodo=periodo, tema=tema.strip(), competencia=comp.strip(),
                      sesiones=sesiones, minutos=int(minutos), contexto=contexto.strip(), adaptar=adaptar)
        try:
            with st.spinner("Generando borrador…"):
                draft = ai.generate(ss.tipo, params, ctx_for(grado))
        except Exception as e:
            return st.error(f"No se pudo generar el borrador: {e}")
        ss.draft, ss.params, ss.step, ss.edit = draft, params, 3, False
        ss.draft_id = db.create_material(params["tema"], ss.tipo, grado, periodo, params["tema"], params, draft)
        reset_checks()
        st.rerun()


def page_revision():
    p, tipo = ss.params, ss.tipo
    if ss.pop("_reset_checks", False):
        for i in range(3):
            ss[f"chk{i}"] = False
    secs = ai.SECTIONS[tipo]

    st.markdown('<div class="step">Paso 3 de 3 · Revisión obligatoria</div>', unsafe_allow_html=True)
    st.title(f"Borrador: {p['tema']}, {p['grado']}")
    st.progress(1.0)
    left, right = st.columns([2, 1])

    with left, st.container(border=True):
        st.markdown('<div class="warn">Contenido generado por IA. Verifique datos y ejemplos antes de usarlo.</div>', unsafe_allow_html=True)
        st.write("")
        for k, label, _ in secs:
            st.markdown(f"**{label}**")
            if ss.edit:
                st.text_area(label, ss.draft[k], key=f"ed_{k}", height=160, label_visibility="collapsed")
            else:
                st.markdown(ss.draft[k])

        def save_edits():
            for k, _, _ in secs:
                ss.draft[k] = ss[f"ed_{k}"]
            db.update_material(ss.draft_id, content=ss.draft)
            ss.edit = False
            reset_checks()

        if ss.edit:
            st.button("Guardar cambios", on_click=save_edits, type="primary")
        else:
            a, b, c, d = st.columns([1, 1.3, 1.6, 1])
            a.button("Editar texto", on_click=lambda: ss.update(edit=True))
            target = c.selectbox("Sección", [k for k, _, _ in secs], format_func=dict((k, l) for k, l, _ in secs).get,
                                 key="regen_key", label_visibility="collapsed")
            if b.button("Regenerar sección"):
                try:
                    with st.spinner("Regenerando…"):
                        ss.draft[target] = ai.regenerate_section(tipo, p, ctx_for(p["grado"]), ss.draft, target)
                    db.update_material(ss.draft_id, content=ss.draft)
                    reset_checks()
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo regenerar: {e}")

    with right:
        with st.container(border=True):
            st.subheader("Lista de verificación")
            c0 = st.checkbox("Los datos y ejemplos son correctos (sin alucinaciones)", key="chk0")
            c1 = st.checkbox("El contenido es pertinente al currículo y a El Tambo", key="chk1")
            c2 = st.checkbox("No contiene datos personales de estudiantes", key="chk2")
        ok = c0 and c1 and c2 and not ss.edit
        with st.container(border=True):
            st.caption("Exportar se habilita al marcar las tres casillas.")
            title = f"{TIPOS[tipo]}: {p['tema']}"
            meta = f"{p['grado']} · {p['periodo']} · {p['sesiones']} sesión(es) de {p['minutos']} min · Inglés"
            sections = [(l, ss.draft[k]) for k, l, _ in secs] if ok else []
            mark = lambda: db.update_material(ss.draft_id, estado="Revisado")
            st.download_button("Exportar a Word", exporter.to_docx(title, meta, sections) if ok else b"", f"{p['tema']}.docx",
                               disabled=not ok, on_click=mark, type="primary", use_container_width=True)
            st.download_button("Exportar a PDF", exporter.to_pdf(title, meta, sections) if ok else b"", f"{p['tema']}.pdf",
                               disabled=not ok, on_click=mark, use_container_width=True)
        st.button("Volver a mis materiales", on_click=go, args=("Mis materiales",))


def page_materiales():
    a, b = st.columns([4, 1])
    a.title("Mis materiales")
    a.caption("Todo lo que has generado y revisado, listo para reutilizar.")
    b.button("Nuevo material", type="primary", on_click=lambda: ss.update(page="Nuevo", tipo=None, draft=None, step=2))
    f = st.columns(4)
    search = f[0].text_input("Buscar", placeholder="Título o tema")
    tipo = f[1].selectbox("Tipo", ["Todos"] + list(TIPOS.values()))
    grado = f[2].selectbox("Grado", ["Todos"] + GRADOS)
    estado = f[3].selectbox("Estado", ["Todos", "Revisado", "Pendiente de revisión"])
    inv = {v: k for k, v in TIPOS.items()}
    rows = db.list_materials(search, inv.get(tipo), None if grado == "Todos" else grado, None if estado == "Todos" else estado)
    with st.container(border=True):
        if not rows:
            st.caption("No hay materiales con esos filtros.")
        for m in rows:
            c = st.columns([3, 1.2, 0.8, 1.2, 1.6, 0.9, 1])
            c[0].write(m["title"])
            c[1].write(TIPOS[m["tipo"]])
            c[2].write(m["grado"])
            c[3].write(m["created_at"][:10])
            c[4].write("✅ Revisado" if m["estado"] == "Revisado" else "⏳ Pendiente")
            c[5].button("Abrir", key=f"o{m['id']}", on_click=open_material, args=(m["id"],))
            c[6].button("Duplicar", key=f"d{m['id']}", on_click=db.duplicate_material, args=(m["id"],))


def page_contexto():
    st.title("Contexto curricular")
    st.caption("Lo que la IA usa para que el material sea pertinente a la institución y a El Tambo.")
    if not ss.coord:
        st.markdown('<div class="warn">Solo el coordinador edita; los docentes consultan.</div>', unsafe_allow_html=True)
    grado = st.radio("Grado", GRADOS, index=5, horizontal=True)
    raw = db.get_curriculum_raw(grado)
    dis = not ss.coord
    with st.form(f"ctx_{grado}"):
        comp = st.text_area(f"Competencias de inglés · {grado} (una por línea)", raw["competencias"], disabled=dis, height=100)
        st.markdown("**Temas por periodo** (uno por línea)")
        cols = st.columns(4)
        ps = [cols[i].text_area(f"Periodo {i + 1}", raw[f"p{i + 1}"], disabled=dis, height=120, key=f"p{i}_{grado}") for i in range(4)]
        ej = st.text_area("Ejemplos del contexto de El Tambo (uno por línea)", raw["ejemplos"], disabled=dis, height=100,
                          placeholder="Plaza de mercado\nFinca cafetera\nCamino al colegio")
        if st.form_submit_button("Guardar contexto", type="primary", disabled=dis):
            db.save_curriculum(grado, comp, *ps, ej)
            st.success("Contexto guardado.")


def page_seguro():
    st.title("Uso seguro de la IA")
    st.caption("Lectura corta de 3 minutos antes de generar su primer material.")
    a, b, c = st.columns(3)
    with a, st.container(border=True, height=420):
        st.subheader("¿Qué es una alucinación?")
        st.write("Es cuando la IA responde con mucha seguridad algo que no es cierto. Es como un estudiante que no estudió "
                 "pero contesta con aplomo: suena bien, pero puede estar mal.")
        st.markdown("**Por eso nada se exporta sin su revisión.**")
    with b, st.container(border=True, height=420):
        st.subheader("Datos que nunca debe escribir")
        st.markdown("- Nombres de estudiantes\n- Números de documento\n- Notas, diagnósticos o situaciones familiares\n- Teléfonos y direcciones")
        st.caption("La ley colombiana de protección de datos personales (Ley 1581 de 2012) protege especialmente los datos de niños, niñas y adolescentes.")
    with c, st.container(border=True, height=420):
        st.subheader("Cómo verificar un borrador")
        st.markdown("1. Revise que fechas, nombres y datos sean ciertos\n2. Compruebe que el tema esté en el plan de estudios\n"
                    "3. Cambie ejemplos que no se parezcan a su aula\n4. Marque la lista de verificación y exporte")
    st.success("¿Listo para crear su primer material?")
    st.button("Ir al inicio", on_click=go, args=("Inicio",), type="primary")


{"Inicio": page_inicio, "Nuevo": page_nuevo, "Mis materiales": page_materiales,
 "Contexto curricular": page_contexto, "Uso seguro de IA": page_seguro}[ss.page]()
