import streamlit as st
import requests
import pandas as pd

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="SmartDocs AI", layout="wide")

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login / Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            res = requests.post(f"{API}/login", json={"username": u, "password": p})
            if res.json().get("status") in ["ok", "success"]:
                st.session_state.user = u
                st.success("Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid login")

    with tab2:
        u2 = st.text_input("New Username", key="reg_user")
        p2 = st.text_input("New Password", type="password", key="reg_pass")

        if st.button("Register"):
            res = requests.post(f"{API}/register", json={"username": u2, "password": p2})
            st.success("Registered! Now login")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.selectbox(
    "Summary Type",
    ["Short", "Detailed", "Bullet", "ELI5"]
)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------- TITLE ----------------
st.title(f"🤖 SmartDocs AI — {st.session_state.user}")

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "🔗 Share"])

# ================== CHAT ==================
with tab1:

    if "messages" not in st.session_state:
        st.session_state.messages = []

    uploaded_file = st.file_uploader("📄 Upload File", type=["pdf", "txt"])

    if uploaded_file:
        st.success(f"📁 {uploaded_file.name} uploaded")

        if st.button("🚀 Process Document"):
            with st.spinner("Processing..."):
                res = requests.post(
                    f"{API}/summarize",
                    files={"file": uploaded_file},
                    data={"mode": mode}
                )

                if res.status_code == 200:
                    summary = res.json().get("summary", "")
                    st.subheader("📄 Summary")
                    st.write(summary)
                else:
                    st.error("Error processing file")

    st.subheader("💬 Ask Questions")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask something...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        res = requests.post(
            f"{API}/ask",
            json={
                "question": user_input,
                "username": st.session_state.user
            }
        )

        if res.status_code == 200:
            answer = res.json().get("answer", "")
        else:
            answer = "❌ Error"

        st.session_state.messages.append({"role": "assistant", "content": answer})

        with st.chat_message("assistant"):
            st.markdown(answer)

# ================== DASHBOARD ==================
with tab2:

    st.subheader("📊 Analytics Dashboard")

    res = requests.get(f"{API}/analytics/{st.session_state.user}")

    if res.status_code == 200:
        data = res.json()

        st.metric("Total Questions", data.get("total_questions", 0))

        st.subheader("🧠 Recent Questions")
        for q in data.get("recent", []):
            st.write("•", q)

    st.subheader("📜 Full History")

    res = requests.get(f"{API}/history/{st.session_state.user}")

    if res.status_code == 200:
        history = res.json().get("history", [])

        if history:
            df = pd.DataFrame(history)

            st.dataframe(df)

            # chart
            st.line_chart(df.index)

            # download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download History", csv, "history.csv")

            # expandable
            for h in history[::-1]:
                with st.expander(h["q"][:60]):
                    st.write("Q:", h["q"])
                    st.write("A:", h["a"])

        else:
            st.info("No history yet")

# ================== SHARE ==================
with tab3:

    st.subheader("🔗 Share Document")

    if st.button("Generate Share Link"):
        res = requests.post(f"{API}/share")

        if res.status_code == 200:
            url = res.json().get("url", "")
            st.success("Share this link:")
            st.code(url)
        else:
            st.error("Failed to generate link")