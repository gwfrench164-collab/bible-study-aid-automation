"""Read-only transcript presentation for the library search window."""
import re
from flask import render_template_string
from query_bible_study import ABBREVIATION_MAP, BOOK_PATTERNS

BOOKS = {name.lower(): name for name in BOOK_PATTERNS}
BOOKS.update(ABBREVIATION_MAP)
BOOKS["psalm"] = "Psalms"
book_names = "|".join(re.escape(b) for b in sorted(BOOKS, key=len, reverse=True))
REFERENCE = re.compile(rf"\b({book_names})\.?\s+(\d+):(\d+(?:\s*[-–]\s*\d+)?)\b", re.I)


def paragraphs(text):
    for block in re.split(r"\n\s*\n", text.strip()):
        words = []
        for word in block.split():
            words.append(word)
            if len(words) >= 120 or (len(words) >= 45 and re.search(r'[.!?][”"’)]*$', word)):
                yield " ".join(words)
                words = []
        if words:
            yield " ".join(words)


def render_reader(path, return_url, actions, query, pattern):
    original = path.read_bytes().decode("utf-8-sig", errors="replace")
    sections = []
    for paragraph in paragraphs(original):
        parts = []
        start = 0
        for match in REFERENCE.finditer(paragraph):
            parts.append((paragraph[start:match.start()], None))
            reference = f"{BOOKS[match[1].lower()]} {match[2]}:{match[3]}"
            parts.append((match[0], reference))
            start = match.end()
        parts.append((paragraph[start:], None))
        sections.append(parts)
    return render_template_string(PAGE, **locals(), title=path.name,
                                  search_pattern=pattern.pattern if pattern else "")


PAGE = r"""
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf9f5;color:#282622;font:16px system-ui}
header,main{max-width:78ch;margin:auto;padding:1rem}nav,.tools{display:flex;gap:.65rem;align-items:center;flex-wrap:wrap}
.tools{position:sticky;top:0;background:#faf9f5;border-block:1px solid #d8d4cd;padding:.65rem;z-index:1;justify-content:center}
button,input,select{font:inherit;padding:.25rem}article{font:20px/1.65 Georgia,serif;overflow-wrap:anywhere}
pre{white-space:pre-wrap;font:inherit}mark{background:#fff1a0}mark.active{background:#ffbf69;outline:2px solid #785128}
h1{overflow-wrap:anywhere}a{color:#254e78}
</style><header><nav><a href="{{return_url}}">← Back to results</a>
{% if 'chunk=' in actions %}<a href="/open?{{actions}}">Selected passage</a>{% endif %}
<a href="/open?{{actions}}&amp;native=1">Open Source</a><a href="/reveal?{{actions}}">Show in Finder</a></nav><h1>{{title}}</h1></header>
<div class="tools"><label>View <select id="mode"><option>Reading</option><option>Original</option></select></label>
<label>Font <select id="font"><option value="Georgia,serif">Serif</option><option value="system-ui">Sans serif</option></select></label>
<label>Size <input type="range" id="size" min="14" max="34" value="20"></label>
<label>Spacing <select id="spacing"><option>1.65</option><option>1.4</option><option>2</option></select></label>
<label>Find <input type="search" id="find" value="{{query}}"></label><button id="prev">Previous</button><button id="next">Next</button>
<span id="count" role="status"></span><button id="copy">Copy text</button><span id="status" role="status"></span></div>
<main><article id="reader"></article></main>
<template id="reading">{% for parts in sections %}<p>{% for text,ref in parts %}{% if ref %}<span data-kjv-reference="{{ref}}">{{text}}</span>{% else %}{{text}}{% endif %}{% endfor %}</p>{% endfor %}</template>
<script>
const el=id=>document.getElementById(id), reader=el('reader'), original={{original|tojson}};
let hits=[], active=0, initial=true;
function select(i,scroll){
  hits[active]?.classList.remove('active'); active=i;
  const hit=hits[i]; hit?.classList.add('active');
  if(hit && scroll) hit.scrollIntoView({block:'center'});
  el('count').textContent=hits.length?(i+1)+' of '+hits.length:(el('find').value?'No matches':'');
  el('prev').disabled=el('next').disabled=hits.length<2;
}
function render(scroll=false){
  reader.replaceChildren();
  if(el('mode').value==='Original'){const pre=document.createElement('pre');pre.textContent=original;reader.append(pre);}
  else reader.append(el('reading').content.cloneNode(true));
  hits=[];active=0;
  const term=el('find').value;
  const seed={{search_pattern|tojson}};
  const pattern=initial && seed ? seed : term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  if(pattern){
    const rx=new RegExp(pattern,'gi'), walker=document.createTreeWalker(reader,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode()) nodes.push(walker.currentNode);
    for(const node of nodes){
      const str=node.data, fragment=document.createDocumentFragment();let end=0;
      for(const match of str.matchAll(rx)){
        fragment.append(str.slice(end,match.index));const mark=document.createElement('mark');
        mark.textContent=match[0];fragment.append(mark);hits.push(mark);end=match.index+match[0].length;
      }
      if(end){fragment.append(str.slice(end));node.replaceWith(fragment);}
    }
  }
  select(0,scroll);
}
function move(delta){if(hits.length)select((active+delta+hits.length)%hits.length,true);}
el('prev').onclick=()=>move(-1);el('next').onclick=()=>move(1);
el('find').oninput=()=>{initial=false;render(true);};
el('find').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();move(e.shiftKey?-1:1);}};
el('mode').onchange=()=>render();
function typography(){reader.style.fontFamily=el('font').value;reader.style.fontSize=el('size').value+'px';reader.style.lineHeight=el('spacing').value;}
for(const id of ['font','size','spacing']){
  const control=el(id);try{const v=localStorage.getItem('reader.'+id);if(v)control.value=v;}catch{}
  control.oninput=()=>{typography();try{localStorage.setItem('reader.'+id,control.value);}catch{}};
}
function selected(){const s=getSelection();return s.rangeCount && reader.contains(s.anchorNode) && reader.contains(s.focusNode)?s.toString():'';}
reader.addEventListener('copy',e=>{const text=selected();if(text){e.preventDefault();e.clipboardData.setData('text/plain',text);}});
el('copy').onclick=async()=>{
  const text=selected() || (el('mode').value==='Original'?original:Array.from(reader.children,p=>p.textContent).join('\n\n'));
  try{await navigator.clipboard.writeText(text);el('status').textContent='Copied';}
  catch{const box=document.createElement('textarea');box.value=text;document.body.append(box);box.select();
    el('status').textContent=document.execCommand('copy')?'Copied':'Select text and press ⌘C';box.remove();}
};
typography();render();
</script></html>"""
