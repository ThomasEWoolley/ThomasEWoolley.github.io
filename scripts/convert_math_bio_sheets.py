#!/usr/bin/env python3
"""Convert the five current Dropbox LaTeX problem sheets to public HTML.

Usage: python scripts/convert_math_bio_sheets.py /path/to/Problem_sheets
Requires Pandoc. Input can also be a flat directory of Sheet_1.tex, etc.
Excluded Answ environments and LaTeX comments never enter the public output.
"""
from pathlib import Path
import argparse
import hashlib
import html
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MACROS = r"""
\newcommand{\D}[2]{\frac{\partial #1}{\partial #2}}
\newcommand{\DD}[2]{\frac{\partial^2 #1}{\partial #2^2}}
\newcommand{\rd}{\text{ d}}
\newcommand{\eg}{\emph{e.g.} }
\newcommand{\ie}{\emph{i.e.} }
\newcommand{\bm}[1]{\boldsymbol{#1}}
\renewcommand{\l}{\left(}
\renewcommand{\r}{\right)}
"""
ALT = {
    'CDC_image.jpg': 'Flattening the epidemic curve: a lower peak spreads cases over a longer period.',
    'Ricker_r1.png': 'Ricker map with r = 1.',
    'Ricker_r21.png': 'Ricker map with r = 2.1.',
    'Ricker_r3.png': 'Ricker map with r = 3.',
    'Push_pull_taxis.png': 'Discrete movement schematic with local pushing rate r and neighbouring pulling rate s.',
    'Nonlocal_motion.png': 'Nonlocal jumps between a population and its three neighbouring boxes in each direction.',
    'Spots_GS.png': 'Spotted pattern in the Gray–Scott model.',
    'Labyrinthine_GS.png': 'Labyrinthine pattern in the Gray–Scott model.',
    'Chaotic_GS.png': 'Example of an evolving pattern in the Gray–Scott model.',
    'PDE_q1.png': 'First steady state morphogen profile for the model construction question.',
    'PDE_q2.png': 'Second steady state morphogen profile for the model construction question.',
    'PDE_q3.png': 'Third steady state morphogen profile for the model construction question.',
    'Discrete_inverse_cubic.png': 'Bifurcation diagram for the inverse cubic population map, with a logarithmic vertical axis.',
    'SquirrelMap.png': 'Maps showing changes in the distribution of red and grey squirrels in the United Kingdom.',
    'Dictyo_pattern.jpg': 'Frame from a video of spatial waves formed by aggregating Dictyostelium discoideum.',
    'Diffusive_motion.png': 'Schematic of unbiased diffusive movement between neighbouring populations.',
    'Attractant_controlled_motion.png': 'Schematic of chemotactic movement controlled by attractant at neighbouring positions.',
}


def pandoc(source, output='html5'):
    result = subprocess.run(['pandoc', '-f', 'latex', '-t', output, '--mathjax', '--wrap=none'],
                            input=MACROS + source, text=True, capture_output=True)
    if result.returncode or result.stderr.strip():
        raise ValueError(result.stderr)
    return result.stdout


def group(s, start, opening='{', closing='}'):
    while s[start].isspace():
        start += 1
    if s[start] != opening:
        raise ValueError(f'Expected {opening} at {s[start:start+60]!r}')
    depth = 1
    i = start + 1
    while depth:
        if s[i] == opening and s[i-1] != '\\':
            depth += 1
        elif s[i] == closing and s[i-1] != '\\':
            depth -= 1
        i += 1
    return s[start+1:i-1], i


def strip_comments(s):
    # Listings are verbatim: percent signs and every code line must survive.
    parts = re.split(r'(\\begin\{lstlisting\}.*?\\end\{lstlisting\})', s, flags=re.S)
    return ''.join(p if p.startswith(r'\begin{lstlisting}') else
                   re.sub(r'(?<!\\)%[^\n]*', '', p) for p in parts)


def key(label):
    return 'ref-' + label.encode().hex()


class Sheet:
    def __init__(self, source, number):
        self.number = number
        self.source = source
        self.refs = {}
        self.fragments = {}
        self.eq = self.fig = self.section = 0
        self.current = ''
        self.lists = []
        self.counters = {}

    def fragment(self, markup):
        token = f'HTMLFRAGMENT{len(self.fragments):04d}TOKEN'
        self.fragments[token] = markup
        return '\n\n' + token + '\n\n'

    def anchor(self, label, value):
        if label in self.refs:
            raise ValueError(f'Duplicate label: {label}')
        self.refs[label] = str(value)
        return f'<span id="{key(label)}"></span>'

    def reference(self, m):
        label = m[2]
        if label not in self.refs:
            raise ValueError(f'Sheet {self.number}: unresolved reference {label!r}')
        value = self.refs[label]
        if m[1] == 'eqref':
            value = '(' + value + ')'
        return r'\href{#' + key(label) + '}{' + value + '}'

    def references(self, s):
        substitutions = {
            'eqns': r'equations \eqref{#1} and \eqref{#2}',
            'eqnto': r'equations \eqref{#1}–\eqref{#2}',
            'figs': r'figures \ref{#1} and \ref{#2}',
            'eqn': r'equation \eqref{#1}', 'fig': r'Figure \ref{#1}',
            'see': r'(see Figure \ref{#1})', 'sect': r'Section \ref{#1}',
        }
        for command, template in substitutions.items():
            count = 2 if '#2' in template else 1
            pattern = r'\\' + command + r'\b' + r'\{([^}]+)\}' * count
            def expand(m):
                result = template
                for i in range(count):
                    result = result.replace(f'#{i+1}', m[i+1])
                return result
            s = re.sub(pattern, expand, s)
        return re.sub(r'\\(eqref|ref)\{([^}]+)\}', self.reference, s)

    def equation(self, m):
        env, body = m[1], m[2]
        # Assign explicit tags so textual references work before MathJax loads.
        rows = re.split(r'\\\\', body) if env == 'align' else [body]
        anchors = ''
        rendered = []
        for row in rows:
            labels = re.findall(r'\\label\{([^}]+)\}', row)
            if r'\nonumber' not in row:
                self.eq += 1
                anchors += ''.join(self.anchor(label, self.eq) for label in labels)
                row = re.sub(r'\\label\{[^}]+\}', '', row) + rf'\tag{{{self.eq}}}'
            else:
                row = row.replace(r'\nonumber', '')
            rendered.append(row)
        body = r'\\'.join(rendered)
        if env == 'align':
            body = r'\begin{align}' + body + r'\end{align}'
        else:
            body = r'\begin{equation*}' + body + r'\end{equation*}'
        # Pandoc expands the mathematical macros, then writes MathJax delimiters.
        markup = pandoc(body).strip()
        # Pandoc uses aligned, which cannot carry a separate tag on each row.
        # Restore the AMS align environment for MathJax's equation numbering.
        if env == 'align':
            markup = markup.replace(r'\begin{aligned}', r'\begin{align}').replace(r'\end{aligned}', r'\end{align}')
        return self.fragment('<div class="equation">' + anchors + markup + '</div>')

    def figure(self, m):
        self.fig += 1
        body = m[1]
        cap = re.search(r'\\caption\s*\{', body)
        caption, cap_end = group(body, cap.end()-1)
        main_labels = re.findall(r'\\label\{([^}]+)\}', caption)
        caption = re.sub(r'\\label\{[^}]+\}', '', caption)
        anchors = ''.join(self.anchor(label, self.fig) for label in main_labels)
        pictures = body[:cap.start()]
        subs = []
        pos = 0
        while (sm := re.search(r'\\subfigure\s*\[', pictures[pos:])):
            start = pos + sm.start()
            sc, end = group(pictures, pos + sm.end()-1, '[', ']')
            content, pos = group(pictures, end)
            letter = chr(97 + len(subs))
            labels = re.findall(r'\\label\{([^}]+)\}', sc)
            subanchors = ''.join(self.anchor(label, f'{self.fig}({letter})') for label in labels)
            sc = re.sub(r'\\label\{[^}]+\}', '', sc).strip()
            subs.append((subanchors, f'({letter}) ' + sc, content))
        if not subs:
            subs = [('', '', pictures)]
        # Caption references are rendered after the complete label map is known.
        token = self.fragment(('figure', self.fig, anchors, caption, subs))
        return token

    def render_figure(self, data):
        _, number, anchors, caption, subs = data
        parts = []
        for subanchors, sc, content in subs:
            image = re.search(r'\\includegraphics(?:\[.*?\])?\{([^}]+)\}', content, flags=re.S)
            name = Path(image[1]).name
            if name not in ALT or not (ROOT / 'Math_bio/images' / name).is_file():
                raise ValueError(f'Missing figure/alternative text: {name}')
            caption_html = pandoc(self.references(sc)).strip() if sc else ''
            parts.append(f'<div class="subfigure">{subanchors}<img src="images/{name}" loading="lazy" alt="{html.escape(ALT[name], quote=True)}">{caption_html}</div>')
        caption_html = pandoc(self.references(caption)).strip()
        return f'<figure>{anchors}<div class="figure-panels">' + ''.join(parts) + f'</div><figcaption><strong>Figure {number}.</strong> {caption_html}</figcaption></figure>'

    def convert(self):
        s = strip_comments(self.source)
        s = s.split(r'\begin{document}', 1)[1].split(r'\end{document}', 1)[0]
        s, n = re.subn(r'\\begin\{Answ\}.*?\\end\{Answ\}', '', s, flags=re.S)
        if r'\begin{Answ}' in s or n != self.source.count(r'\begin{Answ}'):
            raise ValueError('Unbalanced answer environments')
        for command in ('lstset', 'title', 'author'):
            while m := re.search(r'\\' + command + r'\s*\{', s):
                _, end = group(s, m.end()-1)
                s = s[:m.start()] + s[end:]
        s = s.replace(r'\maketitle', '').replace(r'\bb', r'\begin{equation}').replace(r'\ee', r'\end{equation}')
        s = re.sub(r'\\verb ([^\s]+) ', lambda m: r'\verb|' + m[1] + '| ', s)
        # Protect listing content from all structural processing.
        s = re.sub(r'\\begin\{lstlisting\}(.*?)\\end\{lstlisting\}',
                   lambda m: self.fragment('<pre class="matlab"><code>' + html.escape(m[1].strip('\n')) + '</code></pre>'), s, flags=re.S)
        pattern = re.compile(
            r'\\begin\{(equation|align)\}(.*?)\\end\{\1\}'
            r'|\\begin\{figure\}(?:\[[^]]*\])?(.*?)\\end\{figure\}'
            r'|\\section(\*?)\{(.*?)\}'
            r'|\\(begin|end)\{(?:enumerate|itemize)\}'
            r'|\\item\b'
            r'|\\setcounter\{([^}]+)\}\{\\value\{([^}]+)\}\}'
            r'|\\label\{([^}]+)\}', re.S)
        def structural(m):
            if m[1]:
                return self.equation(m)
            if m[3] is not None:
                class FigureMatch:
                    def __getitem__(_, i): return m[3]
                return self.figure(FigureMatch())
            if m[4] is not None:
                if not m[4]:
                    self.section += 1
                    self.current = str(self.section)
                # Nested TeX in the ode45 heading is completed by the source's final brace.
                return r'\subsection*{' + (f'{self.section}. ' if not m[4] else '') + m[5] + '}'
            if m[6]:
                if m[6] == 'begin':
                    self.lists.append(0 if 'enumerate' in m[0] else None)
                else:
                    self.lists.pop()
                return m[0]
            if m[0] == r'\item':
                if self.lists and self.lists[-1] is not None:
                    self.lists[-1] += 1
                    depth = sum(value is not None for value in self.lists)
                    self.current = str(self.lists[-1]) if depth == 1 else chr(96+self.lists[-1])
                return m[0]
            if m[7]:
                name, source = m[7], m[8]
                if name.startswith('Counter'):
                    self.counters[name] = self.lists[-1]
                    return ''
                value = self.counters[source]
                self.lists[-1] = value
                return rf'\setcounter{{{name}}}{{{value}}}'
            return self.fragment(self.anchor(m[9], self.current)).strip()
        s = pattern.sub(structural, s)
        s = self.references(s)
        output = pandoc(s)
        for token, value in self.fragments.items():
            if isinstance(value, tuple):
                value = self.render_figure(value)
            output = output.replace('<p>' + token + '</p>', value).replace(token, value)
        if re.search(r'HTMLFRAGMENT|\\(?:ref|eqref|eqn|fig)\b|\[Answ\]', output):
            raise ValueError('Unconverted source remains')
        return output, n


def page(content, number):
    nav = ''.join(f'<a href="Sheet_{i}.html"' + (' aria-current="page"' if i == number else '') + f'>Sheet {i}</a>' for i in range(1, 6))
    return f'''<!doctype html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Mathematical Biology MA4309: problem sheet {number}, with equations, figures and exercises.">
  <title>Mathematical Biology: problem sheet {number} | Thomas E. Woolley</title>
  <link rel="canonical" href="https://thomaswoolley.co.uk/Math_bio/Sheet_{number}.html">
  <link rel="icon" href="../favicon.ico">
  <link rel="stylesheet" href="../assets/css/site.css">
  <link rel="stylesheet" href="../assets/css/problem-sheets.css">
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="site-header"><div class="container header-inner">
    <a class="site-name" href="../index.html">Dr Thomas E. Woolley</a>
    <nav aria-label="Course navigation"><a href="../lecturing.html#mathematical-biology">Teaching resources</a></nav>
  </div></header>
  <main id="main-content" class="sheet-page">
    <header class="page-heading"><div class="container narrow">
      <p class="eyebrow">MA4309 · Mathematical Biology</p>
      <h1>Problem sheet {number}</h1>
      <p>Thomas E. Woolley</p>
      <p><a href="Sheet_{number}.pdf">Download the PDF</a></p>
      <nav class="sheet-nav" aria-label="Problem sheets">{nav}</nav>
    </div></header>
    <article class="container narrow sheet-content">
      <noscript><p>Enable JavaScript to render the mathematics, or <a href="Sheet_{number}.pdf">download the PDF</a>.</p></noscript>
{content}
    </article>
    <nav class="container narrow sheet-nav bottom-nav" aria-label="More problem sheets">{nav}</nav>
  </main>
  <footer class="site-footer"><div class="container footer-inner">Copyright Thomas E. Woolley, unless otherwise stated.</div></footer>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    for i in range(1, 6):
        path = args.source / f'Sheet{i}/Sheet_{i}.tex'
        if not path.exists():
            path = args.source / f'Sheet_{i}.tex'
        source = path.read_text(encoding='utf-8')
        sheet = Sheet(source, i)
        content, excluded = sheet.convert()
        (ROOT / f'Math_bio/Sheet_{i}.html').write_text(page(content, i), encoding='utf-8')
        print(f'Sheet {i}: {sheet.section} sections, {sheet.eq} equations, {sheet.fig} figures; {excluded} answer sections excluded; source SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
