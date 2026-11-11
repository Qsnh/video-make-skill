import difflib, re

NEUTRAL_PROMPT = "以下是普通话的句子。"

ZH_NUM = {"零": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "两": "2"}


def norm(s):
    s = s.lower().replace("下划线", "_").replace("点", ".")
    s = "".join(ZH_NUM.get(c, c) for c in s)
    return re.sub(r"[\s，。？、！,.?：；:“”\"'_\-（）()·]", "", s)


def score(want, got):
    return difflib.SequenceMatcher(None, norm(want), norm(got)).ratio()
