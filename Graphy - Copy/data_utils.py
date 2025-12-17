import os
import json
import streamlit as st
import warnings
import pandas as pd
import time

# Correct import for tree select
from streamlit_tree_select import tree_select

# Auth imports
from auth import check_authentication, logout, display_sidebar_logo, check_feature_access

# Try Oracle DB import (safe)
try:
    import oracledb
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False

# Suppress pandas warnings
warnings.filterwarnings("ignore")

# Constants
BASE_DIRECTORY = "."
DEFAULT_DIRECTORY = os.path.join(BASE_DIRECTORY, "data")
CONFIG_FILE = os.path.join(BASE_DIRECTORY, "config.json")
CREDENTIALS_FILE = os.path.join(BASE_DIRECTORY, "db_credentials.json")

# Query dictionary (same as before, shortened here for clarity)
QUERIES = {
    "Devices": {
        "sql": "SELECT * FROM devices_table",   # shortened for demo
        "file_name": "devices.csv"
    },
    "Transactions": {
        "sql": "SELECT * FROM transactions_table",   # shortened for demo
        "file_name": "transactions.csv"
    }
}

# ----------------- CONFIG FUNCTIONS -----------------
def load_app_config():
    config = {"directory": DEFAULT_DIRECTORY}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config.update(json.load(f))
                if not os.path.isdir(config.get("directory")):
                    config["directory"] = DEFAULT_DIRECTORY
        except Exception as e:
            st.error(f"Error loading config: {e}")
    return config

def save_app_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        return True
    except Exception as e:
        st.error(f"Error saving config: {e}")
        return False

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
                for key, value in credentials.items():
                    os.environ[key] = value
                return credentials
        except Exception as e:
            st.error(f"Error loading credentials: {e}")
    return {}

def save_credentials(credentials):
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(credentials, f)
        for key, value in credentials.items():
            os.environ[key] = value
        return True
    except Exception as e:
        st.error(f"Error saving credentials: {e}")
        return False

def get_stored_directory():
    return load_app_config().get("directory", DEFAULT_DIRECTORY)

def save_directory(directory):
    if os.path.isdir(directory):
        config = load_app_config()
        config["directory"] = directory
        return save_app_config(config)
    else:
        st.error("Invalid directory. Falling back to default.")
        return False

@st.cache_data
def build_directory_tree(path):
    label = "IbisPulse" if path == BASE_DIRECTORY else os.path.basename(path) or path
    tree = {"label": label, "value": path}
    try:
        children = [
            build_directory_tree(os.path.join(path, name))
            for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name))
        ]
        if children:
            tree["children"] = children
    except PermissionError:
        pass
    return tree

# ----------------- FORM FUNCTIONS -----------------
def initialize_form_fields():
    credentials = load_credentials()
    return {
        'input_username': credentials.get('DB_USERNAME', ''),
        'input_password': credentials.get('DB_PASSWORD', ''),
        'input_host': credentials.get('DB_HOST', ''),
        'input_port': credentials.get('DB_PORT', ''),
        'input_service_name': credentials.get('DB_SERVICE_NAME', ''),
    }

def display_form_fields(values):
    col1, col2 = st.columns([1, 1.5])
    with col1:
        values['input_username'] = st.text_input("DB Username:", value=values['input_username'], key='input_username')
        values['input_password'] = st.text_input("DB Password:", value=values['input_password'], type="password", key='input_password')
        values['input_host'] = st.text_input("DB Host:", value=values['input_host'], key='input_host')
        values['input_service_name'] = st.text_input("DB Service Name:", value=values['input_service_name'], key='input_service_name')
        values['input_port'] = st.text_input("DB Port:", value=values['input_port'], key='input_port')
    return values

def save_form():
    if 'form_values' in st.session_state:
        form = st.session_state['form_values']
        if all(form.get(key) for key in ['input_username','input_password','input_host','input_port','input_service_name']):
            credentials = {
                'DB_USERNAME': form['input_username'],
                'DB_PASSWORD': form['input_password'],
                'DB_HOST': form['input_host'],
                'DB_PORT': form['input_port'],
                'DB_SERVICE_NAME': form['input_service_name']
            }
            if save_credentials(credentials):
                st.success("✅ Credentials saved.")
            else:
                st.error("❌ Failed to save credentials.")
        else:
            st.error("❌ Please fill all fields.")

def reset_form_fields():
    st.session_state['form_values'] = {
        'input_username': '', 'input_password': '',
        'input_host': '', 'input_port': '',
        'input_service_name': '',
    }
    for key in ['input_username','input_password','input_host','input_service_name','input_port']:
        st.session_state.pop(key, None)
    st.session_state['reset_clicked'] = True
    save_credentials({k:'' for k in ['DB_USERNAME','DB_PASSWORD','DB_HOST','DB_PORT','DB_SERVICE_NAME']})
    return

# ----------------- DB FUNCTIONS -----------------
@st.cache_data(ttl=600)
def run_query(sql):
    if not ORACLE_AVAILABLE:
        st.error("❌ Oracle driver not installed. Please install with `pip install oracledb`.")
        return pd.DataFrame()

    username = os.environ.get('DB_USERNAME', '')
    password = os.environ.get('DB_PASSWORD', '')
    host = os.environ.get('DB_HOST', '')
    port = os.environ.get('DB_PORT', '')
    service_name = os.environ.get('DB_SERVICE_NAME', '')
    dsn = f"{host}:{port}/{service_name}"

    try:
        with oracledb.connect(user=username, password=password, dsn=dsn) as conn:
            return pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

def fetch_all_data():
    data_directory = get_stored_directory()
    if not os.path.exists(data_directory):
        try:
            os.makedirs(data_directory)
        except Exception as e:
            st.error(f"Error creating directory: {e}")
            return False

    success = True
    status_container = st.empty()
    total_queries = len(QUERIES)

    for i, (name, cfg) in enumerate(QUERIES.items()):
        status_container.info(f"⏳ Running {name} query...")
        df = run_query(cfg["sql"])
        if df.empty:
            status_container.error(f"❌ No data for {name}.")
            success = False
        else:
            file_path = os.path.join(data_directory, cfg["file_name"])
            try:
                df.to_csv(file_path, index=False)
                status_container.success(f"✅ {name} data saved")
            except Exception as e:
                status_container.error(f"❌ Error saving {name}: {e}")
                success = False
    return success

def refresh_data():
    run_query.clear()
    if all(os.environ.get(k) for k in ['DB_USERNAME','DB_PASSWORD','DB_HOST','DB_PORT','DB_SERVICE_NAME']):
        fetch_all_data()
    else:
        st.sidebar.warning("⚠️ Please enter DB credentials first.")
        time.sleep(2)
    st.session_state['refetch_data'] = False
    st.rerun()
