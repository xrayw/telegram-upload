import hanlp

HanLP = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH)

def gen_tags(text):
    words = HanLP(text)
    tokens = words.get('tok/fine')
    if not tokens:
        return text
    if not text.startswith("#"):
        text = '#' + text
    if len(tokens) == 1:
        return text
    return '\n'.join((text, ' '.join(t if t.startswith('#') else '#' + t for t in tokens)))
