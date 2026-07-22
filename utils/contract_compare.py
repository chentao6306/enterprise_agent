import difflib

def compare_contracts(text1, text2):
    d = difflib.unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile='合同A',
        tofile='合同B',
        lineterm=''
    )
    diff_result = ''.join(d)
    if not diff_result:
        return "两份合同内容完全一致。"
    return diff_result