# Entry point for Streamlit Community Cloud
import runpy

if __name__ == "__main__":
    runpy.run_module("app_ui", run_name="__main__")
else:
    import app_ui
