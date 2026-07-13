# TODO (MediChain Flask debug)

- [ ] Repair `app.py` to guarantee navigation works with existing `href="*.html"` links.
- [ ] Ensure every `render_template()` target exists and is reachable via predictable endpoints.
- [ ] Add safe catch-all routes to reduce 500/TemplateNotFound from mismatched endpoints.
- [ ] Restart server and verify: `/`, `/login.html`, `/hospital_registration.html`, and at least one page per role.
- [ ] Run a template scanner (Python-based, since ripgrep is unavailable) to find broken `url_for()`/`include`/asset paths.
- [ ] Fix broken `url_for()` endpoints and missing assets by adjusting routes or template references.
