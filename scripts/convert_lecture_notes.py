#!/usr/bin/env python3
"""Render both complete lecture-note courses from their unmodified Dropbox LaTeX.
Usage: python scripts/convert_lecture_notes.py /path/to/notes-source
Requires Pandoc, pdfLaTeX, Pillow and PyMuPDF. Only Master.tex's included chapters
are published. Generated diagrams preserve TikZ, and references span the full book.
"""
from pathlib import Path
import argparse,collections,hashlib,html,json,re,shutil,subprocess,io,os
import fitz
from PIL import Image
from convert_math_bio_sheets import group,strip_comments
ROOT=Path(__file__).resolve().parents[1]
MACROS=r'''
\newcommand{\D}[2]{\frac{\partial #1}{\partial #2}}
\newcommand{\DD}[2]{\frac{\partial^2 #1}{\partial #2^2}}
\newcommand{\rd}{\mathrm{d}}
\newcommand{\eg}{\emph{e.g.} }
\newcommand{\ie}{\emph{i.e.} }
\newcommand{\bm}[1]{\boldsymbol{#1}}
\newcommand{\bu}{\boldsymbol{u}}
\newcommand{\bn}{\boldsymbol{n}}
\newcommand{\tr}{\mathrm{tr}}
\newcommand{\slashed}[1]{\not{#1}}
\newcommand{\restr}[2]{\left.#1\right|_{#2}}
\renewcommand{\l}{\left(}
\renewcommand{\r}{\right)}
'''
CONFIG={
'Math_bio_course':dict(title='Mathematical Biology',code='MA4309',folder='Math_bio',pdf='Master.pdf',anchor='mathematical-biology'),
'ODE_course':dict(title='Modelling with Differential Equations',code='MA0232',folder='ODE',pdf='../files/Master_2.pdf',anchor='modelling-with-differential-equations'),
}
def pandoc(s):
 p=subprocess.run(['pandoc','-f','latex','-t','html5','--mathjax','--wrap=none'],input=MACROS+s,text=True,capture_output=True)
 if p.returncode:raise ValueError(p.stderr)
 if p.stderr.strip():raise ValueError(p.stderr)
 return p.stdout

def unwrap(s,command,nargs=1):
 pattern=r'\\'+command+r'\b\s*\{'
 while m:=re.search(pattern,s):
  pos=m.end()-1;args=[]
  for i in range(nargs):v,pos=group(s,pos);args.append(v)
  s=s[:m.start()]+args[-1]+s[pos:]
 return s

def clean_math(s):
 s=re.sub(r'\\ie\b',lambda m:r'\textit{i.e.} ',s)
 s=re.sub(r'\\eg\b',lambda m:r'\textit{e.g.} ',s)
 s=re.sub(r'\\noalign\s*\{\\medskip\}', '', s)
 s=re.sub(r'\\(begin|end)\s+\{',r'\\\1{',s)
 while m:=re.search(r'\\colvec\s*\{',s):
  n,pos=group(s,m.end()-1);items=[]
  for i in range(int(n)):v,pos=group(s,pos);items.append(v)
  s=s[:m.start()]+r'\begin{pmatrix}'+r'\\'.join(items)+r'\end{pmatrix}'+s[pos:]
 return s

def rows(s):
 """Split align rows without splitting nested matrices or arrays."""
 result=[];start=0;depth=0
 for m in re.finditer(r'\\begin\{[^}]+\}|\\end\{[^}]+\}|\\\\(?:\[[^]]*\])?',s):
  if m[0].startswith('\\begin'):depth+=1
  elif m[0].startswith('\\end'):depth-=1
  elif depth==0:result.append(s[start:m.start()]);start=m.end()
 result.append(s[start:]);return result

def plain(s):
 s=re.sub(r'\\(?:label|ref)\{[^}]*\}','',s)
 s=re.sub(r'\\(?:textit|textbf|emph)\{([^}]*)\}',r'\1',s)
 s=re.sub(r'\\[A-Za-z]+','',s);return re.sub(r'[{}$]','',s).strip()

class Book:
 def __init__(self,source,course,config):
  self.source=source;self.course=course;self.cfg=config;self.refs={};self.fragments={};self.chapter=0;self.appendix=False
  self.section=[0,0,0];self.eq=self.fig=self.thm=self.tab=0;self.example=self.defin=0;self.current='';self.toc=[];self.diagrams=[];self.images=set();self.audit=[]
  self.out=ROOT/config['folder'];self.asset=self.out/'notes-images';self.asset.mkdir(parents=True,exist_ok=True)
  self.master=(source/course/'Latex/Master.tex').read_text();self.preamble=self.master.split(r'\begin{document}')[0]
 def token(self,value,inline=False):
  key=f'NOTESFRAGMENT{len(self.fragments):05d}TOKEN';self.fragments[key]=value
  return key if inline else '\n\n'+key+'\n\n'
 def number(self):return chr(64+self.chapter) if self.appendix else str(self.chapter)
 def anchor(self,label,value=None):
  if label in self.refs:raise ValueError('Duplicate label '+label)
  self.refs[label]=str(value if value is not None else self.current)
  return '<span id="ref-'+label.encode().hex()+'"></span>'
 def labels(self,s,value):
  labels=re.findall(r'\\label\{([^}]+)\}',s)
  return re.sub(r'\\label\{[^}]+\}','',s),''.join(self.anchor(l,value) for l in labels)
 def references(self,s):
  for cmd,name,n in [('eqns','equations',2),('eqnto','equations',2),('figs','Figures',2),('eqn','equation',1),('fig','Figure',1),('see','see Figure',1),('sect','Section',1),('app','Appendix',1),('chap','Chapter',1)]:
   def expand(m):
    vals=[('\\eqref' if cmd.startswith('eq') else '\\ref')+'{'+x+'}' for x in m.groups()]
    out=name+' '+('–' if cmd=='eqnto' else ' and ').join(vals)
    return '('+out+')' if cmd=='see' else out
   s=re.sub(r'\\'+cmd+r'\b'+r'\{([^}]+)\}'*n,expand,s)
  def ref(m):
   if m[2] not in self.refs:raise ValueError('Unresolved reference '+m[2])
   value=self.refs[m[2]]
   if m[1]=='eqref':value='('+value+')'
   return '\\href{#ref-'+m[2].encode().hex()+'}{'+value+'}'
  return re.sub(r'\\(ref|eqref)\{([^}]+)\}',ref,s)
 def image(self,name,alt):
  base=Path(name).name;candidates=[]
  for directory in [self.source/self.course/'Pictures',ROOT/'Pictures',ROOT/'Math_bio/images',ROOT.parent/'website/Pictures']:
   candidates.extend([directory/base,directory/(base+'.png'),directory/(base+'.pdf')])
  p=next((p for p in candidates if p.exists()),None)
  if not p:raise ValueError('Missing image '+name)
  digest=hashlib.sha256(p.read_bytes()).hexdigest()[:12];filename='image-'+digest+'.webp';dest=self.asset/filename
  if not dest.exists():
   if p.suffix=='.pdf':
    doc=fitz.open(p);pix=doc[0].get_pixmap(matrix=fitz.Matrix(2,2));im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
   else:im=Image.open(p)
   im.thumbnail((2000,1600));buffer=io.BytesIO();im.save(buffer,'WEBP',lossless=True)
   temporary=dest.with_suffix('.tmp');temporary.write_bytes(buffer.getvalue());temporary.replace(dest)
  with Image.open(dest) as im:w,h=im.size
  self.images.add(filename)
  return f'<img src="notes-images/{filename}" width="{w}" height="{h}" loading="lazy" alt="{html.escape(alt,quote=True)}">'
 def diagram(self,tex,alt):
  digest=hashlib.sha256(tex.encode()).hexdigest()[:12];name='diagram-'+digest+'.svg';self.diagrams.append((tex,name,alt));return f'<img class="latex-diagram" src="notes-images/{name}" loading="lazy" alt="{html.escape(alt,quote=True)}">'
 def equation(self,env,body):
  body=clean_math(body)
  anchors='';parts=[]
  for row in rows(body) if env.startswith('align') else [body]:
   numbered=r'\nonumber' not in row and not env.endswith('*') and bool(row.strip())
   if numbered:self.eq+=1
   value=f'{self.number()}.{self.eq}'
   row,a=self.labels(row,value);anchors+=a
   row=row.replace(r'\nonumber','')
   if numbered:row+=r'\tag{'+value+'}'
   parts.append(row)
  body=r'\\'.join(parts)
  tex=r'\begin{'+('align*' if env.startswith('align') else 'equation*')+'}'+body+r'\end{'+('align*' if env.startswith('align') else 'equation*')+'}'
  if r'\tikz' in body:markup=self.diagram(tex,'Non-dimensionalisation balances, with arrows marking the terms being balanced.')
  else:markup='<div class="math display">\\['+html.escape(clean_math(tex))+'\\]</div>'
  return self.token('<div class="equation">'+anchors+markup+'</div>')
 def figure(self,body):
  self.fig+=1;number=f'{self.number()}.{self.fig}'
  cap=re.search(r'\\caption\s*\{',body)
  if cap:caption,end=group(body,cap.end()-1);pictures=body[:cap.start()];tail=body[end:]
  else:caption='';pictures=body;tail=''
  caption,anchors=self.labels(caption,number);tail,a=self.labels(tail,number);anchors+=a
  subs=[];pos=0
  while m:=re.search(r'\\subfigure\s*\[',pictures[pos:]):
   sc,end=group(pictures,pos+m.end()-1,'[',']');content,pos=group(pictures,end)
   letter=chr(97+len(subs));sc,sa=self.labels(sc,f'{number}({letter})');subs.append((sa,'('+letter+') '+sc,content))
  if not subs:subs=[('','',pictures)]
  return self.token(('figure',number,anchors,caption,subs))
 def render_figure(self,data):
  _,number,anchors,caption,subs=data;parts=[]
  for sa,sc,content in subs:
   if r'\begin{tikzpicture}' in content:image=self.diagram(content,'Stability regions and typical trajectories in the trace–determinant plane.')
   else:
    im=re.search(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',content)
    if not im:raise ValueError('No figure content '+content[:100])
    alt=re.sub(r'^\([a-z]\)\s*', '', plain(sc)) or Path(im[1]).stem.replace('_',' ')
    image=self.image(im[1],alt)
   parts.append('<div class="subfigure">'+sa+image+pandoc(self.references(sc))+'</div>')
  return '<figure>'+anchors+'<div class="figure-panels">'+''.join(parts)+'</div><figcaption><strong>Figure '+number+'.</strong> '+pandoc(self.references(caption))+'</figcaption></figure>'
 def table(self,body):
  self.tab+=1
  number=f'{self.number()}.{self.tab}'
  caption=''
  if m:=re.search(r'\\caption\s*\{',body):
   caption,end=group(body,m.end()-1);body=body[:m.start()]+body[end:]
  caption,anchors=self.labels(caption,number)
  body,a=self.labels(body,number);anchors+=a
  body=unwrap(body,'resizebox',3)
  # Pandoc understands multirow spans and retains the cells and mathematical text.
  return self.token(('table',body,anchors,caption,number))
 def transform(self,s):
  s=strip_comments(s);s=unwrap(s,'COL')
  for old,new in [('Chapter','chapter'),('Section','section'),('Subsection','subsection'),('Subsubsection','subsubsection')]:
   s=re.sub(r'\\'+old+r'\{([^}]+)\}',lambda m:'\\'+new+'{'+m[1]+'}\\label{'+m[1]+'}',s)
  s=s.replace(r'\bb',r'\begin{equation}').replace(r'\ee',r'\end{equation}')
  s=s.replace('bolditemize','itemize').replace('todolist','itemize')
  # A source caption contains a bibliographic reference in href's URL position.
  s=re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}',lambda m:m[0] if m[1].startswith(('https://','http://','#')) else m[2]+' ('+m[1]+')',s)
  pattern=re.compile(r'\\begin\{(?P<math>equation\*?|align\*?)\}(?P<mathbody>.*?)\\end\{(?P=math)\}'
   r'|\\begin\{figure\}(?:\[[^]]*\])?(?P<figure>.*?)\\end\{figure\}'
   r'|\\begin\{table\}(?:\[[^]]*\])?(?P<table>.*?)\\end\{table\}'
   r'|\\(?P<head>chapter|section|subsection|subsubsection)(?P<star>\*?)\s*\{'
   r'|\\(?P<endenv>begin|end)\{(?P<env>example\*?|defin|thm|cor|lem|proof|cboxed|tcolorbox|aquote)\}'
   r'|\\(?P<appendix>appendix)\b'
   r'|\\label\{(?P<label>[^}]+)\}'
   r'|\\includegraphics(?:\[[^]]*\])?\{(?P<image>[^}]+)\}',re.S)
  out=[];pos=0;stack=[]
  while m:=pattern.search(s,pos):
   out.append(s[pos:m.start()]);pos=m.end()
   if m['math']:out.append(self.equation(m['math'],m['mathbody']))
   elif m['figure'] is not None:out.append(self.figure(m['figure']))
   elif m['table'] is not None:out.append(self.table(m['table']))
   elif m['head']:
    title,pos=group(s,pos-1);level=['chapter','section','subsection','subsubsection'].index(m['head'])
    if level==0:
     self.chapter+=1;self.section=[0,0,0];self.eq=self.fig=self.thm=self.tab=0
    elif not m['star']:
     self.section[level-1]+=1
     for i in range(level,3):self.section[i]=0
     if level==1:self.thm=0
    self.current='.'.join([self.number()]+[str(n) for n in self.section[:level]])
    ident='heading-'+str(len(self.toc));self.toc.append((level,self.current,title,ident));out.append(self.token(('heading',level,self.current,title,ident)))
   elif m['appendix']:self.appendix=True;self.chapter=0
   elif m['label']:out.append(self.token(self.anchor(m['label']),True))
   elif m['image']:out.append(self.token(self.image(m['image'],Path(m['image']).stem.replace('_',' '))))
   else:
    env=m['env']
    if m['endenv']=='end':
     if not stack or stack.pop()!=env:raise ValueError('Unbalanced '+env)
     out.append(self.token('</div>'))
    else:
     stack.append(env);option=''
     if pos<len(s) and s[pos]=='[':option,pos=group(s,pos,'[',']')
     title={'example':'Example','example*':'Example','defin':'Definition','thm':'Theorem','cor':'Corollary','lem':'Lemma','proof':'Proof','cboxed':'','tcolorbox':'','aquote':''}[env]
     if env.startswith('example'):
      self.example+=1;self.current=f'{self.number()}.{self.section[0]}.{self.example}';title+=' '+self.current
      option=option.removeprefix('frametitle=')
     elif env=='defin':self.defin+=1;self.current=str(self.defin);title+=' '+self.current
     elif env in ('thm','cor','lem'):self.thm+=1;self.current=f'{self.number()}.{self.section[0]}.{self.thm}';title+=' '+self.current
     elif env=='aquote':option,pos=group(s,pos)
     option,anchors=self.labels(option,self.current)
     out.append(self.token(('env',env,title,option,anchors)))
  out.append(s[pos:]);assert not stack,stack
  return ''.join(out)
 def render(self):
  order=re.findall(r'\\include\{([^}]+)\}',strip_comments(self.master))
  chunks=[]
  for name in order:
   p=self.source/self.course/'Latex'/ (name+'.tex');s=p.read_text();self.audit.append({'source':name+'.tex','sha256':hashlib.sha256(p.read_bytes()).hexdigest()});chunks.append(self.transform(s))
  converted=pandoc(self.references(''.join(chunks)))
  for token,data in self.fragments.items():
   if isinstance(data,tuple):
    if data[0]=='figure':value=self.render_figure(data)
    elif data[0]=='table':value='<div class="table-scroll" tabindex="0" role="region" aria-label="Lecture notes table">'+data[2]+pandoc(self.references(data[1]))+('<p><strong>Table '+data[4]+'.</strong> '+pandoc(self.references(data[3]))+'</p>' if data[3] else '')+'</div>'
    elif data[0]=='heading':
     _,level,num,title,ident=data;value=f'<h{level+2} id="{ident}">{num} '+pandoc(self.references(title)).removeprefix('<p>').removesuffix('\n').removesuffix('</p>')+f'</h{level+2}>'
    else:
     _,env,title,option,anchors=data
     text=title+(': ' if title and option else '')+option
     value=f'<div class="note-block {env}">'+anchors+('<p class="block-title">'+pandoc(self.references(text)).removeprefix('<p>').removesuffix('\n').removesuffix('</p>')+'</p>' if text else '')
   else:value=data
   converted=converted.replace('<p>'+token+'</p>',value).replace(token,value)
  converted=converted.replace('http://','https://')
  if 'NOTESFRAGMENT' in converted:raise ValueError('Unexpanded fragment')
  self.write_page(converted);self.render_diagrams()
  (self.out/'notes-build.json').write_text(json.dumps({'sources':self.audit,'chapters':sum(x[0]==0 for x in self.toc),'labels':len(self.refs),'diagrams':len(self.diagrams),'images':len(self.images)},indent=2)+'\n')
  print(self.course,len(self.refs),'labels,',len(self.toc),'headings,',len(self.images),'images,',len(self.diagrams),'TikZ diagrams')
 def write_page(self,content):
  cfg=self.cfg;toc=''.join('<li class="toc-level-'+str(level)+'"><a href="#'+ident+'">'+num+' '+html.escape(plain(title))+'</a></li>' for level,num,title,ident in self.toc if level<2)
  markup=f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['title']}: lecture notes | Thomas E. Woolley</title>
<meta name="description" content="Complete {cfg['code']} {cfg['title']} lecture notes with worked examples, equations, figures and chapter navigation.">
<link rel="canonical" href="https://thomaswoolley.co.uk/{cfg['folder']}/Master.html">
<link rel="icon" href="../favicon.ico"><link rel="stylesheet" href="../assets/css/site.css"><link rel="stylesheet" href="../assets/css/problem-sheets.css"><link rel="stylesheet" href="../assets/css/lecture-notes.css">
<script>window.MathJax={{loader:{{load:['[tex]/mathtools','[tex]/textmacros']}},tex:{{packages:{{'[+]':['mathtools','textmacros']}},macros:{{D:['\\\\frac{{\\\\partial #1}}{{\\\\partial #2}}',2],DD:['\\\\frac{{\\\\partial^2 #1}}{{\\\\partial #2^2}}',2],rd:'\\\\mathrm{{d}}',bm:['\\\\boldsymbol{{#1}}',1],bu:'\\\\boldsymbol{{u}}',bn:'\\\\boldsymbol{{n}}',tr:'\\\\mathrm{{tr}}',l:'\\\\left(',r:'\\\\right)',restr:['\\\\left.#1\\\\right|_{{#2}}',2],slashed:['\\\\not{{#1}}',1]}}}}}};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script></head>
<body><a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header"><div class="container header-inner"><a class="site-name" href="../index.html">Dr Thomas E. Woolley</a><nav aria-label="Course navigation"><a href="../lecturing.html#{cfg['anchor']}">Teaching resources</a></nav></div></header>
<main class="sheet-page notes-page" id="main-content"><header class="page-heading"><div class="container narrow"><p class="eyebrow">{cfg['code']} · Lecture notes</p><h1>{cfg['title']}</h1><p>Thomas E. Woolley</p><p><a href="{cfg['pdf']}">Download the PDF</a> · <a href="#contents">Contents</a></p></div></header>
<div class="notes-layout container"><aside class="notes-contents" id="contents"><details open><summary>Contents</summary><nav aria-label="Lecture note contents"><ol>{toc}</ol></nav></details></aside><article class="sheet-content notes-content">
<noscript><p>Enable JavaScript to render the equations, or <a href="{cfg['pdf']}">download the PDF</a>.</p></noscript>
{content}
</article></div><a class="back-to-contents" href="#contents">Back to contents</a></main>
<footer class="site-footer"><div class="container footer-inner">Copyright Thomas E. Woolley, unless otherwise stated.</div></footer></body></html>'''
  markup=re.sub(r'<script>window.MathJax=.*?</script>',lambda m:m[0].replace(chr(92)*4,chr(92)*2),markup,count=1)
  (self.out/'Master.html').write_text(markup)
 def render_diagrams(self):
  if not self.diagrams:return
  work=self.source/'diagram-build'/self.course;work.mkdir(parents=True,exist_ok=True)
  # Same preamble as the source, with preview cropping only in this build copy.
  for name in ['soul.sty','soul-ori.sty','ifsym.sty']:
   candidates=[ROOT.parent/'ode/build/Latex'/name]
   for p in candidates:
    if p.exists():shutil.copy(p,work/name);break
  preamble=self.preamble+'\n\\usepackage[active,tightpage]{preview}\n\\setlength\\PreviewBorder{8pt}\n'
  for tex,name,alt in self.diagrams:
   dest=self.asset/name
   if dest.exists():continue
   document=preamble+'\\begin{document}\n\\begin{preview}\n\\begin{minipage}{\\textwidth}\n'+tex+'\n\\end{minipage}\n\\end{preview}\n\\end{document}\n'
   (work/'snippet.tex').write_text(document)
   for i in range(2):
    p=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','snippet.tex'],cwd=work,capture_output=True)
    if p.returncode:raise ValueError(p.stdout.decode(errors='replace')[-1400:])
   doc=fitz.open(work/'snippet.pdf');assert len(doc)==1
   dest.write_text(doc[0].get_svg_image())

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);args=p.parse_args()
 for course,cfg in CONFIG.items():Book(args.source.resolve(),course,cfg).render()
if __name__=='__main__':main()
