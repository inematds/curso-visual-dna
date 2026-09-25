from pathlib import Path
from html import escape
import json
R=Path(__file__).resolve().parent
data=json.loads((R/'context/imagens-codex.json').read_text())
lessons=json.loads((R/'context/aulas-editoriais.json').read_text())
html='''<!doctype html><html lang="pt-BR" data-theme="papel"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/aula.css"><title>Imagens do caso Fio Claro · Visual DNA</title><main class="wrap"><p><a href="curso.html#trilha">Voltar à trilha</a></p><h1>Imagens do caso Fio Claro</h1><p>Ilustrações didáticas criadas com o gerador integrado do Codex. Pessoas, oficina e aplicações são fictícias. Nenhuma imagem comprova um serviço realizado.</p><p>Você pode guardar estas referências para analisar o método. As práticas das aulas 11 e 12 pedem gerações próprias. A cena da aula 1 também ilustra a abertura do curso.</p>'''
for x,d in zip(data,lessons):
 html+=f'<section style="padding:24px 0;border-bottom:1px solid var(--line)"><h2>Aula {x["n"]} · {escape(d["titulo"])}</h2><figure><img style="width:100%;height:auto" src="{x["arquivo"]}" width="1280" height="720" loading="lazy" alt="{escape(d["observacao"])}"><figcaption>{escape(d["observacao"])}</figcaption></figure><p><a href="{x["arquivo"]}" download>Guardar imagem</a> · <a href="curso.html#aula-{x["n"]}">Abrir aula</a></p><details><summary>Pedido de criação e revisão</summary><p>{escape(x["prompt"])}</p><p>{escape(x.get("edicao","Sem edição posterior."))}</p></details></section>'
html+='<p>Pedidos e arquivos de origem registrados no projeto. Conversões para WebP preservam a cena; as alterações criativas foram feitas no gerador do Codex.</p></main></html>'
(R/'galeria.html').write_text(html)
