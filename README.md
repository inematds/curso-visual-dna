# Visual DNA v6.2

Curso gratuito de direção de arte com caso fictício autoral.

Fontes editoriais em context/conteudo-base.json e context/aulas-editoriais.json. Montar com `python3 montar.py`; motor oficial formato-curso-v6 necessário.

Ilustrações geradas com Codex image_gen; o mecanismo não expõe seletor de versão do modelo nesta sessão. Não contém vídeos ou transcrições do material de origem.

## English / Español

[English](https://inematds.github.io/curso-visual-dna/en/) · [Español](https://inematds.github.io/curso-visual-dna/es/)

Textos traduzidos com GPT-6 Luna por subagentes nativos da assinatura Codex, sem API externa. Ilustrações originais compartilhadas; progresso e anotações separados por idioma.

Após montar o português, reaplique os catálogos salvos:

```sh
python3 scripts/i18n_local.py build .
python3 scripts/verify_i18n.py .
node scripts/check_i18n_browser.cjs . /tmp/curso-i18n-checks
```

Requer Python/BeautifulSoup e os pacotes locais Babel/Playwright indicados nos scripts. A montagem não chama modelos nem redes. Mudanças na fonte PT exigem revisar os catálogos `i18n/`. O motor oficial `assets/curso.js` é preservado; a proteção de importação é gerada em `assets/curso-i18n.js` e nas edições traduzidas.

Evidências em `context/validacao-i18n.md`. Revisões por agentes são simuladas, não testes com alunos reais.

<!-- inema-backlink:v1 -->
## Mais no INEMA.CLUB

- [Ficha completa deste curso](https://www.inema.club/cursos/296-visual-dna-direcao-de-arte-e-branding-com-ia-v6-2/)
- [Guia: como aprender inteligência artificial](https://www.inema.club/aprender-inteligencia-artificial/)
- [Todos os cursos](https://www.inema.club/cursos/)
<!-- /inema-backlink:v1 -->
