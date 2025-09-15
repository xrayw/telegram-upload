import jieba

def gen_tags(text):
    tokens = list(jieba.cut(text, cut_all=True))
    if not tokens:
        return text
    if not text.startswith("#"):
        text = '#' + text
    if len(tokens) == 1:
        return text
    return '\n'.join((text, ' '.join(t if t.startswith('#') else '#' + t for t in tokens if t.strip())))
