# LogSense AI

A local, AI-powered tool that highlights unusual patterns in system log files.  
It helps users understand logs without requiring technical knowledge, and all processing stays on the device for privacy and reliability.

---

## 🚀 What It Does
- Takes a text-based log file from **Windows**, **Linux**, **macOS**, and **android**
- Generates embeddings for each log line
- Detects unusual patterns using **IsolationForest**
- Categorizes anomalies as **Low**, **Moderate**, or **High**
- Provides short explanations for clarity
- Runs fully **offline** through a simple local web interface
- Supports **Light / Dark mode** and filtering

---

## 🎯 Why It Exists
System logs hold useful clues, but most people never look at them because they’re overwhelming.  
LogSense AI shows what stands out without acting like an antivirus or recommending deletions.

It **guides attention**, not system actions.

---

## ✨ Features
- Clean, beginner-friendly UI  
- Automatic XML-to-text conversion  
- Color-coded anomaly levels  
- Filtering: All / Moderate+High / High  
- Downloadable analysis report  
- Clear instructions for exporting logs on each OS  
- File size limit for stability  
- Cross-platform (Windows, Linux, macOS, and android)

---

## ❗ What It Is NOT
- Not an antivirus  
- Not a malware detector  
- Not a system cleaner  
- Does not delete or modify files  

---

## 📁 Supported Formats
- `.txt`  
- `.log`  
- `.xml` (auto-converted)  

---

## ▶️ How to Run
1. Install dependencies from **requirements.txt**  
`pip install -r requirements.txt`

3. Run:
`python app.py`

4. Open in your browser:  
**http://localhost:5000**

---

## ⚠️ Disclaimer
- **LogSense AI** cannot confirm threats or detect malware.  
- It only highlights unusual patterns inside log files.  
- Do not delete or modify system files based on the results.  
- When unsure, get help from someone experienced.

---

## 🤝 Contributing
LogSense AI is open source, and contributions are welcome.  
See **CONTRIBUTING.md** for guidelines.

---

## 📄 License
This project is licensed under the **MIT License**.
