"""
Context-aware spelling correction for handwritten lines (noisy-channel model).

Handwriting recognisers make systematic look-alike errors that a language model resolves easily, e.g. a
writer whose "r" looks like "u" yields "leauning" / "buanch" / "fuom". For each suspicious word:

  candidates   dictionary words within 2 edits (SymSpell over an 82k-word English frequency list, plus the
               checkpoint's common-word and medical vocabularies)
  channel      handwriting-aware weighted edit distance: visually confusable substitutions (r/u/w/v/n, a/o/u,
               e/c, l/1/I/t, cl->d, rn->m, ...) are cheap, other edits expensive
  context      a small causal language model scores the whole line with each candidate in place

A word is replaced only when  LM gain - channel_weight * channel_cost - freq_weight * rarity  clears a margin
fitted on validation data (scripts/fit_spell_correction.py). Guardrails: numbers, doses, frequencies, acronyms,
words next to dose/form tokens, medical-lexicon terms and single-word crops are never changed.
"""
import math
import os
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

DEFAULT_PARAMS: Dict[str, float] = {
    "channel_weight": 2.0,   # LM nats one unit of edit cost is worth
    "freq_weight": 0.3,      # penalty per decade of rarity below a common word
    "margin": 1.0,           # minimum net gain (nats) to replace a word
    "min_line_words": 3,     # lines shorter than this have too little context to correct
    # With the line's image (correct_line(image_score=...)), the recogniser's likelihood of each candidate line
    # given the ink joins the gain, and a candidate the ink argues against by more than image_veto nats is
    # never applied. image_weight 0 disables it; fitted by scripts/fit_spell_correction.py --image
    "image_weight": 0.0,
    "image_veto": 1e9,
    # choose_reading: the other recogniser's word replaces this one when the LM prefers it by this many nats
    "reading_margin": 1e9,
    # ...lowered by this many nats when the other word is a clinical term (clinical_terms.txt) and this one is not
    "clinical_prior": 0.0,
}

# Unknown word vs a formulary drug in the other reading: at most two look-alike edits ("ParID" / "PanD")
_DRUG_SWAP_COST = 1.6


def load_clinical_terms(path: Optional[str] = None) -> List[str]:
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinical_terms.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [w for w in (line.split("#", 1)[0].strip().lower() for line in f) if w]
    except OSError:
        return []

# Character groups a handwriting recogniser confuses; substitutions inside a group are cheap
_CONFUSABLE_GROUPS = ["ruwvn", "aou", "ec", "l1it", "il", "oa0", "s5", "g9q", "b6h", "mn", "yv", "z2", "ft", "kh"]
_CONFUSABLE = {(a, b) for g in _CONFUSABLE_GROUPS for a in g for b in g if a != b}
_MULTI = {("rn", "m"), ("m", "rn"), ("cl", "d"), ("d", "cl"), ("ii", "u"), ("u", "ii"), ("ti", "u"), ("u", "ti"), ("vv", "w"), ("w", "vv")}

_DOSE_OR_FORM = re.compile(
    r"^(?:\d[\d./-]*\w*|mg|mcg|ml|gm|g|iu|tab|tabs|cap|caps|syp|inj|oint|od|bd|bid|tid|tds|qid|hs|sos|prn|stat|"
    r"ac|pc|x\d+\w*)\.?$", re.IGNORECASE)


def channel_cost(observed: str, candidate: str) -> float:
    """Weighted edit distance from the true word (candidate) to what the recogniser produced (observed)."""
    a, b = candidate.lower(), observed.lower()
    n, m = len(a), len(b)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i * 0.8
    for j in range(1, m + 1):
        d[0][j] = j * 0.8
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                sub = 0.0
            elif (a[i - 1], b[j - 1]) in _CONFUSABLE:
                sub = 0.35
            else:
                sub = 1.0
            best = min(d[i - 1][j] + 0.8, d[i][j - 1] + 0.8, d[i - 1][j - 1] + sub)
            for src, dst in _MULTI:
                ls, ld = len(src), len(dst)
                if i >= ls and j >= ld and a[i - ls:i] == src and b[j - ld:j] == dst:
                    best = min(best, d[i - ls][j - ld] + 0.4)
            d[i][j] = best
    return d[n][m]


def _match_case(template: str, word: str) -> str:
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


class ContextSpellCorrector:
    def __init__(
        self,
        extra_words: Sequence[str] = (),
        protected_terms: Sequence[str] = (),
        lm_name: str = "distilgpt2",
        device: Optional[str] = None,
        params: Optional[Dict[str, float]] = None,
        clinical_terms: Optional[Sequence[str]] = None,
    ):
        import symspellpy
        from symspellpy import SymSpell

        self.params = dict(DEFAULT_PARAMS)
        self.params.update(params or {})
        self.sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        dict_path = os.path.join(os.path.dirname(symspellpy.__file__), "frequency_dictionary_en_82_765.txt")
        self.sym.load_dictionary(dict_path, term_index=0, count_index=1)
        self.max_count = max(self.sym.words.values())
        for w in extra_words:
            w = w.lower()
            if w.isalpha() and len(w) >= 2 and w not in self.sym.words:
                self.sym.create_dictionary_entry(w, 50_000)  # mid-frequency: valid, but not preferred over common words
        self.protected = {t.lower() for t in protected_terms}
        self._drug_forms: Dict[str, str] = {}  # letters only, lowercase -> the term as written ("pand" -> "Pan-D")
        for t in protected_terms:
            self._drug_forms.setdefault(re.sub(r"[^a-z]", "", t.lower()), t)
        self.clinical = set(load_clinical_terms() if clinical_terms is None else (w.lower() for w in clinical_terms))
        for w in self.clinical:
            if w.isalpha() and w not in self.sym.words:
                self.sym.create_dictionary_entry(w, 50_000)
        self._lm_name = lm_name
        self._device = device
        self._lm = None
        self._tok = None

    # ------------------------------------------------------------------
    def _load_lm(self):
        if self._lm is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(self._lm_name)
            self._tok.pad_token = self._tok.eos_token
            self._lm = AutoModelForCausalLM.from_pretrained(self._lm_name)
            dev = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
            self._lm.to(dev).eval()
            self._dev = dev
        return self._lm, self._tok

    def sentence_logprobs(self, sentences: List[str]) -> List[float]:
        """Total log-probability of each sentence under the language model."""
        import torch
        lm, tok = self._load_lm()
        enc = tok([tok.eos_token + s for s in sentences], return_tensors="pt", padding=True)
        ids = enc.input_ids.to(self._dev)
        mask = enc.attention_mask.to(self._dev)
        with torch.inference_mode():
            logits = lm(input_ids=ids, attention_mask=mask).logits.float()
        logp = torch.log_softmax(logits[:, :-1], dim=-1)
        tgt = ids[:, 1:]
        token_lp = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1) * mask[:, 1:]
        return token_lp.sum(dim=1).tolist()

    def _is_known(self, w: str) -> bool:
        return w in self.sym.words or w in self.protected

    def _rarity(self, w: str) -> float:
        count = self.sym.words.get(w, 1)
        return max(0.0, math.log10(self.max_count / max(1, count)) - 3.0)  # 0 for the ~top few thousand words

    def suspicious(self, tokens: List[str], i: int) -> bool:
        raw = tokens[i]
        core = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", raw)
        if len(core) < 3 or not core.isalpha() or core.isupper():
            return False
        w = core.lower()
        if w in self.protected or self._is_known(w):
            return False
        if i > 0 and core[:1].isupper():
            return False  # mid-line capitalised word: likely a name / brand, never snap to a dictionary word
        neighbours = tokens[max(0, i - 1): i] + tokens[i + 1: i + 2]
        if any(_DOSE_OR_FORM.match(n.strip(",;:")) for n in neighbours):
            return False  # likely a drug name next to its dose / form: never snap to English
        return True

    def _candidates(self, core: str, max_candidates: int) -> List[str]:
        from symspellpy import Verbosity
        sugg = self.sym.lookup(core.lower(), Verbosity.ALL, max_edit_distance=2, include_unknown=False)
        return sorted({s.term for s in sugg if s.term != core.lower()},
                      key=lambda t: (channel_cost(core, t), -self.sym.words.get(t, 0)))[:max_candidates]

    def suggest(self, tokens: List[str], i: int, n: int = 3, max_candidates: int = 8) -> List[str]:
        """Best replacements for tokens[i] in its line, best first. No acceptance margin: a reviewer chooses."""
        m = re.match(r"^([^A-Za-z]*)([A-Za-z]+)([^A-Za-z]*)$", tokens[i])
        if not m:
            return []
        pre, core, post = m.groups()
        cands = self._candidates(core, max_candidates)
        if not cands:
            return []
        variants = [" ".join(tokens[:i] + [f"{pre}{_match_case(core, c)}{post}"] + tokens[i + 1:]) for c in cands]
        scores = self.sentence_logprobs(variants)
        ranked = sorted(zip(cands, scores), key=lambda cs: -(cs[1] - self.params["channel_weight"] * channel_cost(core, cs[0])
                                                              - self.params["freq_weight"] * self._rarity(cs[0])))
        return [_match_case(core, c) for c, _ in ranked[:n]]

    def reading_swaps(self, text: str, other: str) -> List[Tuple[int, str]]:
        """
        Words where the other recogniser's reading of the line has a different known word in the same place:
        (token index, that word). Lines that do not align (the other reading is garbled) give nothing.
        """
        import difflib
        a, b = text.split(), (other or "").split()
        if not a or not b:
            return []
        sm = difflib.SequenceMatcher(a=[w.lower() for w in a], b=[w.lower() for w in b], autojunk=False)
        if sm.ratio() < 0.5:
            return []
        swaps = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "replace" or i2 - i1 != j2 - j1:
                continue
            for k in range(i2 - i1):
                mine = re.match(r"^[^A-Za-z]*([A-Za-z][A-Za-z'-]*[A-Za-z])[^A-Za-z]*$", a[i1 + k])
                theirs = re.match(r"^[^A-Za-z]*([A-Za-z][A-Za-z'-]*[A-Za-z])[^A-Za-z]*$", b[j1 + k])
                if not mine or not theirs or mine.group(1).lower() == theirs.group(1).lower():
                    continue
                w, alt = mine.group(1).lower(), theirs.group(1).lower()
                if not self._is_known(alt) or (w in self.protected and alt not in self.protected):
                    continue  # only real words; a drug name is never traded for an English word
                swaps.append((i1 + k, theirs.group(1)))
        return swaps

    def drug_swaps(self, text: str, other: str) -> List[Tuple[int, str]]:
        """
        Unknown words where the other reading holds a formulary drug a look-alike edit or two away, even when the
        other reader ran it into its dose ("Tab ParID 40mg" / "Tab. PanD40nmg" -> Pan-D): (token index, drug).
        """
        letters = lambda s: re.sub(r"[^a-z]", "", s.lower())
        drugs = []
        for run in re.findall(r"[A-Za-z][A-Za-z-]*[A-Za-z]", other or ""):
            form = self._drug_forms.get(letters(run))
            if form and len(letters(run)) >= 3 and form not in drugs:
                drugs.append(form)
        if not drugs:
            return []
        tokens = text.split()
        present = {letters(t) for t in tokens}
        swaps = []
        for i, tok in enumerate(tokens):
            m = re.match(r"^[^A-Za-z]*([A-Za-z][A-Za-z'-]*[A-Za-z])[^A-Za-z]*$", tok)
            if not m or len(letters(m.group(1))) < 4 or self._is_known(m.group(1).lower()):
                continue
            close = [(channel_cost(letters(m.group(1)), letters(d)), d) for d in drugs if letters(d) not in present]
            close = [cd for cd in close if cd[0] <= _DRUG_SWAP_COST]
            if close:
                swaps.append((i, min(close)[1]))
        return swaps

    def choose_reading(self, text: str, other: str) -> Tuple[str, List[Dict]]:
        """
        Where the two recognisers read a word differently:
          - an unknown word becomes the formulary drug the other reading spells (drug_swaps), without the LM;
          - where the other reading is a known word ("gun paint" / "gum paint"), the language model picks the
            reading that fits the line, by at least reading_margin nats (less clinical_prior for a clinical term).
        """
        tokens = text.split()
        changes = []
        for i, drug in self.drug_swaps(text, other):
            m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z'-]*[A-Za-z])([^A-Za-z]*)$", tokens[i])
            changes.append({"from": m.group(2), "to": drug, "reason": "drug in other reading"})
            tokens[i] = f"{m.group(1)}{drug}{m.group(3)}"
        text = " ".join(tokens)
        swaps = self.reading_swaps(text, other)
        if not swaps:
            return text, changes
        for i, alt in swaps:
            m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z'-]*[A-Za-z])([^A-Za-z]*)$", tokens[i])
            if not m:
                continue
            pre, core, post = m.groups()
            new_core = _match_case(core, alt)
            variant = tokens[:i] + [f"{pre}{new_core}{post}"] + tokens[i + 1:]
            base, new = self.sentence_logprobs([" ".join(tokens), " ".join(variant)])
            if new - base > self.params["reading_margin"] - self._clinical_bonus(core, alt):
                changes.append({"from": core, "to": new_core, "gain": round(new - base, 2), "reason": "other reading"})
                tokens = variant
        return " ".join(tokens), changes

    def _clinical_bonus(self, word: str, alt: str) -> float:
        w, a = word.lower(), alt.lower()
        if a in self.clinical and w not in self.clinical and w not in self.protected:
            return self.params["clinical_prior"]
        return 0.0

    def correct_line(self, text: str, max_candidates: int = 8,
                     image_score: Optional[Callable[[List[str]], List[float]]] = None) -> Tuple[str, List[Dict]]:
        """
        image_score(lines) -> log-likelihood of each line given the line's crop (MedicalHTREngine.score_texts);
        used when the fitted image_weight is non-zero.
        """
        tokens = text.split()
        if len(tokens) < self.params["min_line_words"]:
            return text, []
        use_image = image_score is not None and self.params["image_weight"] > 0
        changes = []
        for i in range(len(tokens)):
            if not self.suspicious(tokens, i):
                continue
            raw = tokens[i]
            m = re.match(r"^([^A-Za-z]*)([A-Za-z]+)([^A-Za-z]*)$", raw)
            if not m:
                continue
            pre, core, post = m.groups()
            cands = self._candidates(core, max_candidates)
            if not cands:
                continue
            variants = [" ".join(tokens[:i] + [f"{pre}{_match_case(core, c)}{post}"] + tokens[i + 1:]) for c in cands]
            scores = self.sentence_logprobs([" ".join(tokens)] + variants)
            base = scores[0]
            img = [0.0] * (len(cands) + 1)
            if use_image:
                try:
                    img = image_score([" ".join(tokens)] + variants)
                except Exception:
                    use_image = False
            best, best_gain, best_img = None, self.params["margin"], None
            for c, s, im in zip(cands, scores[1:], img[1:]):
                img_gain = im - img[0]
                if use_image and img_gain < -self.params["image_veto"]:
                    continue  # the ink argues against this word
                gain = (s - base) - self.params["channel_weight"] * channel_cost(core, c) \
                    - self.params["freq_weight"] * self._rarity(c) + self.params["image_weight"] * img_gain
                if gain > best_gain:
                    best, best_gain, best_img = c, gain, img_gain
            if best:
                tokens[i] = f"{pre}{_match_case(core, best)}{post}"
                change = {"from": core, "to": _match_case(core, best), "gain": round(best_gain, 2)}
                if use_image:
                    change["image_gain"] = round(best_img, 2)
                changes.append(change)
        return " ".join(tokens), changes
