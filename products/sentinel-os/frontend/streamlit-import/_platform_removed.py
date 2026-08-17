import streamlit as st

from sentinel_os.platform.backend.api.control import submit_module_execution
from sentinel_os.platform.backend.platform.operations_platform import (
    get_dagda_status,
    get_module_definitions,
)


def render_module_form(module_key, title, description, fields):
    st.subheader(title)
    st.caption(description)

    with st.form(f"form-{module_key}"):
        values = {}

        if "target" in fields:
            values["target"] = st.text_input("Target", key=f"{module_key}-target")

        if "image_name" in fields:
            values["image_name"] = st.text_input("Docker image name", key=f"{module_key}-image")

        if "cluster_ip" in fields:
            values["cluster_ip"] = st.text_input("Cluster IP or domain", key=f"{module_key}-cluster")

        if "flags_extras" in fields:
            values["flags_extras"] = st.text_input("Extra flags", key=f"{module_key}-flags")

        if "hash_text" in fields:
            values["hash_text"] = st.text_area("Hash text", key=f"{module_key}-hash")

        submitted = st.form_submit_button(f"Run {title}")

    if submitted:
        result = submit_module_execution(module_key, values)

        st.session_state.setdefault("platform_results", {})
        st.session_state.platform_results[module_key] = result

    if module_key == "dagda":
        status = get_dagda_status()
        st.info(f"Dagda service status: {'online' if status else 'offline'}")

    if st.session_state.get("platform_results", {}).get(module_key) is not None:
        st.json(st.session_state.platform_results[module_key])


def render_platform():
    st.set_page_config(
        page_title="Sentinel Operations Platform",
        page_icon="🛠️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Sentinel Operations Platform")
    st.caption("Direct control surface for Sentinel module execution.")

    definitions = get_module_definitions()
    st.sidebar.title("Modules")
    st.sidebar.markdown("Directly execute the live module implementations.")

    tabs = st.tabs([definition.title for definition in definitions])

    for tab, definition in zip(tabs, definitions):
        with tab:
            render_module_form(
                definition.key,
                definition.title,
                definition.description,
                definition.fields,
            )


def main():
    render_platform()


if __name__ == "__main__":
    main()