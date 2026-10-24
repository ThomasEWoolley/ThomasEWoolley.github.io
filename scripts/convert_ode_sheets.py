#!/usr/bin/env python3
"""Regenerate ODE HTML sheets from current Dropbox sources, preserving answer visibility."""
from pathlib import Path
import argparse,html,re
import convert_math_bio_sheets as base
ROOT=base.ROOT
base.MACROS += r'\newcommand{\slashed}[1]{\not{#1}}\newcommand{\myvec}[1]{\begin{pmatrix}#1\end{pmatrix}}\newcommand{\degree}{^{\circ}}'
ALT={
'Turin_shroud.jpg':'The Shroud of Turin.', 'True_lies.png':'Schematic of the jump in True Lies, with the horizontal and vertical distances marked.',
'Possible_trajectories.png':'Five candidate trajectory sketches for classifying monotonicity and possible ODE models.',
'TBP_orbits.png':'Simulated planetary orbits around a central mass.', 'TBP_circle.png':'Three equal masses moving around a circle.',
'Polars.png':'Cartesian and polar position vectors and unit vectors.', 'Kepler.png':'Equal areas swept out by an orbiting planet over equal time intervals.',
'Two_body_problem.png':'Positions and gravitational forces for two planets.', 'Two_body_problem_new_origin.png':'The relative position of the second planet with the first planet as the origin.',
'Orbit_a_025.png':'Polar orbit for alpha = 0.25.', 'Orbit_a_1.png':'Circular orbit for alpha = 1.', 'Orbit_a_4.png':'Elliptical orbit for alpha = 4.',
'Michaelis-Menten_schematic.png':'Enzyme binding, complex formation and product release in Michaelis-Menten kinetics.',
'Michaelis-Menten_approximation.png':'Full and approximate Michaelis-Menten solutions over time.',
'Spruce_budworm.jpg':'Spruce budworm in moth and larval stages.', 'Spruce_budworm_r_medium.png':'Spruce budworm growth curve for an intermediate value of r.',
'f1_f2.png':'Growth and predation functions for increasing r at fixed r divided by k.',
'f1_f2_positivity.png':'Regions where growth exceeds predation and where predation exceeds growth.',
'Spruce_budworm_r_small_arrowed.png':'Spruce budworm steady states and trajectory directions for small r.',
'Spruce_budworm_r_medium_arrowed.png':'Spruce budworm steady states and trajectory directions for intermediate r.',
'Spruce_budworm_r_large_arrowed.png':'Spruce budworm steady states and trajectory directions for large r.',
'Revision_stability_one_variable.png':'One-variable phase plot showing the stability of five steady states.',
'Lynx_chasing_hare.jpeg':'A lynx chasing a hare.', 'Lynx_hare.png':'Historical records of lynx and hare pelts over time.',
'Lorenz_sims_rho_5.png':'Lorenz trajectories and coordinate projections for rho = 0.5.',
'Lorenz_sims_rho_20.png':'Lorenz trajectories and coordinate projections for rho = 2.',
'Lorenz_sims_rho_280.png':'Chaotic Lorenz trajectories for two nearby initial conditions.',
'Lorenz_chaos.png':'Time series showing divergence of two nearby Lorenz trajectories.',
'red-squirrel-v-squirrel.jpg':'A red squirrel and a grey squirrel.',
'Fitzhugh_Nagumo_sims.png':'FitzHugh-Nagumo trajectories for gamma = 2 and epsilon = 0.001.',
}
class Sheet(base.Sheet):
 def render_figure(self,data):
  _,number,anchors,caption,subs=data;parts=[]
  for subanchors,sc,content in subs:
   m=re.search(r'\\includegraphics(?:\[.*?\])?\{([^}]+)\}',content,re.S);name=Path(m[1]).name
   if name not in ALT or not (ROOT/'Pictures'/name).is_file():raise ValueError('Missing figure/alt: '+name)
   cap=base.pandoc(self.references(sc)).strip() if sc else ''
   parts.append(f'<div class="subfigure">{subanchors}<img src="../Pictures/{name}" loading="lazy" alt="{html.escape(ALT[name],quote=True)}">{cap}</div>')
  return f'<figure>{anchors}<div class="figure-panels">'+''.join(parts)+f'</div><figcaption><strong>Figure {number}.</strong> {base.pandoc(self.references(caption)).strip()}</figcaption></figure>'
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);args=parser.parse_args()
 for i in range(1,6):
  p=args.source/f'Q{i}/Sheet_{i}.tex'
  if not p.exists():p=args.source/f'Sheet_{i}.tex'
  source=p.read_text();included=r'\includecomment{Answ}' in source
  if included:source=source.replace(r'\begin{Answ}','').replace(r'\end{Answ}','')
  source=re.sub(r'\\begin\{ttfamily\}(.*?)\\end\{ttfamily\}',lambda m:'\\begin{lstlisting}'+m[1].replace(r'\%','%')+'\\end{lstlisting}',source,flags=re.S)
  sheet=Sheet(source,i);content,n=sheet.convert()
  markup=base.page(content,i).replace('Mathematical Biology','Modelling with Differential Equations').replace('MA4309','MA0232').replace(f'/Math_bio/Sheet_{i}.html',f'/Q{i}/Sheet_{i}.html').replace('lecturing.html#mathematical-biology','lecturing.html#modelling-with-differential-equations')
  for j in range(1,6):markup=markup.replace(f'href="Sheet_{j}.html"',f'href="../Q{j}/Sheet_{j}.html"')
  markup=markup.replace('http://','https://')
  (ROOT/f'Q{i}/Sheet_{i}.html').write_text(markup)
  print(f'Sheet {i}: {sheet.eq} equations, {sheet.fig} figures; answers '+('included' if included else f'excluded ({n} sections)'))
if __name__=='__main__':main()
