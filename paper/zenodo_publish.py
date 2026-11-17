#!/usr/bin/env python3
"""Zenodo: 发布 med-eval-envs 技术报告 v0（新记录，非版本升级）。"""
import hashlib
import json
import urllib.error
import urllib.request

TOK = open('/home/ubuntu/.hermes/zenodo_token.txt').read().strip()
PDF = '/home/ubuntu/work/med_eval_envs/paper/med_eval_envs_v0.pdf'
NAME = 'med_eval_envs_v0.pdf'
SHA = hashlib.sha256(open(PDF, 'rb').read()).hexdigest()


def call(method, url, data=None, raw=None):
    h = {'Authorization': f'Bearer {TOK}'}
    body = None
    if raw is not None:
        h['Content-Type'] = 'application/octet-stream'
        body = raw
    elif data is not None:
        h['Content-Type'] = 'application/json'
        body = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method, headers=h, data=body), timeout=180) as r:
            t = r.read().decode()
            try:
                return r.status, json.loads(t)
            except Exception:
                return r.status, t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


DESC = (
 "Medical-AI benchmarks usually report a number that a third party cannot re-derive. We describe a small "
 "technical framework in which every task ships three inseparable parts: data with known ground truth, a grader "
 "that reads only a prediction file and a truth file, and a reproducibility veto that voids the whole submission "
 "when the same seed does not reproduce frame-for-frame. Two tasks are implemented &mdash; resting-state EEG "
 "alpha-peak identification and synthetic OCT layer-boundary localisation. Rule-based baselines score 100/100 on "
 "the EEG task and 20% pass-rate on the OCT task. We read the first result as a statement about synthetic data "
 "rather than about EEG: a log-log 1/f fit with residual peak-picking saturates the generator, which is exactly "
 "why the criteria, not the difficulty, are the deliverable at this stage. No clinical claim is made; the data "
 "are synthetic and the framework is not a medical device."
 "<hr/><p>Code, generators, graders, baselines and CI: https://github.com/Even-li316/med-eval-envs (MIT).</p>"
 f"<p>PDF SHA-256: <code>{SHA}</code></p>"
)

meta = {
    "access": {"record": "public", "files": "public"},
    "files": {"enabled": True},
    "metadata": {
        "title": "Auditable Evaluation Environments for Medical Signal and Imaging Tasks: A Technical Report on v0",
        "publication_date": "2026-11-17",
        "resource_type": {"id": "publication-technicalnote"},
        "creators": [{"person_or_org": {"type": "personal", "given_name": "Yafeng",
                                        "family_name": "Li", "name": "Li, Yafeng"}}],
        "description": DESC,
        "license": {"id": "cc-by-4.0"},
        "languages": [{"id": "eng"}],
        "publisher": "Zenodo",
        "subjects": [{"subject": "medical AI evaluation"}, {"subject": "reproducibility"},
                     {"subject": "EEG"}, {"subject": "OCT"}, {"subject": "benchmark"}],
        "related_identifiers": [{"identifier": "https://github.com/Even-li316/med-eval-envs",
                                 "relation_type": {"id": "issupplementedby"}, "scheme": "url",
                                 "resource_type": {"id": "software"}}],
    },
}


def main():
    st, r = call('POST', 'https://zenodo.org/api/records', meta)
    print('create', st)
    if st not in (200, 201):
        print(r); return
    rid = r['id']
    print('draft', rid)
    st, _ = call('POST', f'https://zenodo.org/api/records/{rid}/draft/files', [{'key': NAME}])
    print('init', st)
    st, _ = call('PUT', f'https://zenodo.org/api/records/{rid}/draft/files/{NAME}/content',
                 raw=open(PDF, 'rb').read())
    print('upload', st)
    st, _ = call('POST', f'https://zenodo.org/api/records/{rid}/draft/files/{NAME}/commit')
    print('commit', st)
    st, p = call('POST', f'https://zenodo.org/api/records/{rid}/draft/actions/publish')
    print('publish', st)
    if isinstance(p, dict):
        print('DOI:', p.get('doi'), '| URL:', p.get('links', {}).get('self_html'))
        open('/tmp/med_eval_doi.txt', 'w').write(f"{p.get('doi')}\t{p.get('links',{}).get('self_html')}")


if __name__ == '__main__':
    main()
