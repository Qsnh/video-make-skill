import difflib, re

NEUTRAL_PROMPT = "以下是普通话的句子。"
DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
UNITS = {"十": 10, "百": 100, "千": 1000}


def zh_number(run):
    if not any(c in UNITS for c in run):
        return "".join(str(DIGITS[c]) for c in run)
    total, cur = 0, 0
    for c in run:
        if c in DIGITS:
            cur = DIGITS[c]
        else:
            total += (cur or 1) * UNITS[c]
            cur = 0
    return str(total + cur)


def norm(s):
    s = s.lower().replace("下划线", "_").replace("点", ".")
    s = re.sub(r"[零一二两三四五六七八九十百千]+", lambda m: zh_number(m.group()), s)
    return re.sub(r"[\s，。？、！,.?：；:“”\"'_\-（）()·]", "", s)


def score(want, got):
    return difflib.SequenceMatcher(None, norm(want), norm(got)).ratio()
