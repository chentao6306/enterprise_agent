import re

def detect_sensitive(text):
    patterns = {
        "身份证号": r"\b\d{17}[\dXx]\b",
        "手机号": r"\b1[3-9]\d{9}\b",
        "银行卡号": r"\b\d{16,19}\b",
        "邮箱": r"\b[\w.-]+@[\w.-]+\.\w{2,4}\b"
    }
    findings = []
    for name, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            findings.append({"类型": name, "数量": len(matches), "示例": matches[:2]})
    return findings