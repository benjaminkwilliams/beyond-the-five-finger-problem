#!/usr/bin/env python3
"""Deterministic infographic PNG renderer. No image model or network calls.
Extracted verbatim (except ICON_SVGS, emptied) from the user's gist
'Rounded-card infographic template' v1.1, 2026-10-26. Icons are disabled
in the workflow config, so the embedded icon SVGs are not needed;
see the gist for the full icon set and Apache-2.0 attribution."""
import argparse, copy, hashlib, io, json, math, re, sys
from pathlib import Path
from xml.etree import ElementTree as ET
import yaml
import cairosvg
from PIL import Image, ImageDraw, ImageFont

ICON_SVGS = {}

PALETTE = {
 'red': ['#F26B6B','#2B1D1C','#B83232','#FDECEC'],
 'blue': ['#5C96EA','#1B222C','#245FB5','#EDF4FD'],
 'green': ['#42C798','#10261F','#087A56','#EAF8F1'],
 'amber': ['#E9B44C','#292313','#8A5900','#FFF6E2'],
 'purple': ['#B987EF','#211C29','#7542A8','#F4EDFC'],
 'teal': ['#46CCB3','#0E2724','#087E70','#E8F8F5'],
 'neutral': ['#B9BFBD','#171715','#59635F','#F5F6F5']}

THEMES = {
 'dark': dict(background='#000000',surface='#171715',text='#FFFFFF',
              secondary='#B9BFBD',border='#353A37',connector='#7D8882'),
 'light': dict(background='#FFFFFF',surface='#F5F6F5',text='#171A18',
               secondary='#59635F',border='#D5DCD8',connector='#66736C')}

STYLES = {'container': {'panel'}, 'information': {'tile','card','outlined'},
          'metric': {'card','outlined'}, 'road_sign': {'banner','chevron'}}

def require(condition, message):
 if not condition: raise ValueError(message)

def load(path, preset):
 text = path.read_text(encoding='utf-8')
 if path.suffix.lower()=='.json': configs=[json.loads(text)]
 elif path.suffix.lower() in ('.yaml','.yml'): configs=[yaml.safe_load(text)]
 else:
  configs=[]
  for kind, block in re.findall(r'```(yaml|json)\s*\n(.*?)```',text,re.S):
   obj=json.loads(block) if kind=='json' else yaml.safe_load(block)
   if isinstance(obj,dict) and 'infographic' in obj: configs.append(obj)
 require(configs,'No infographic YAML/JSON configuration found')
 candidates=[o['infographic'] for o in configs]
 if preset.isdigit():
  index=int(preset);require(0<=index<len(candidates),'Preset index out of range');return candidates[index]
 mode={'ecosystem':'absolute','card':'grid'}.get(preset,preset)
 matches=[o for o in candidates if o.get('layout',{}).get('mode','absolute')==mode]
 require(len(matches)==1,'Select one preset: ecosystem, card, or zero-based block index')
 return matches[0]

def blend(a,b,p):
 def rgb(c):return [int(c[i:i+2],16) for i in (1,3,5)]
 return tuple(round(x*p+y*(1-p)) for x,y in zip(rgb(a),rgb(b)))

class Renderer:
 def __init__(self,cfg,args):
  self.c=copy.deepcopy(cfg);self.args=args
  if args.theme:self.c['theme']=args.theme
  self.theme=self.c.get('theme','dark');require(self.theme in THEMES,'Invalid theme')
  self.t=dict(THEMES[self.theme]);self.t.update(self.c.get('theme_tokens',{}))
  self.palette=dict(PALETTE);self.palette.update(self.c.get('palette',{}))
  self.place_aligned_flow()
  self.W=int(self.c['canvas']['width']);self.H=int(self.c['canvas']['height'])
  require(0<self.W<=16000 and 0<self.H<=16000,'Canvas size outside 1..16000')
  self.mode=self.c.get('layout',{}).get('mode','absolute')
  require(self.mode in ['grid','absolute'],'Invalid layout mode')
  self.card=self.c.get('typography','card' if self.mode=='grid' else 'ecosystem')=='card'
  self.scale=self.W/(1600 if self.card else 3200)
  self.im=Image.new('RGB',(self.W,self.H),self.t['background']);self.d=ImageDraw.Draw(self.im)
  self.fonts={};self.font_paths=self.find_fonts()
  self.boxes=self.c.get('boxes',[]);self.by_id={b['id']:b for b in self.boxes}
  require(len(self.by_id)==len(self.boxes),'Duplicate box IDs')
  self.buses={b['id']:b for b in self.c.get('buses',[])}
  require(len(self.buses)==len(self.c.get('buses',[])),'Duplicate bus IDs')
  require(not(set(self.buses)&set(self.by_id)),'Bus and box IDs must differ')
  for b in self.boxes:
   require(b.get('role') in STYLES,f"Invalid role: {b['id']}")
   default={'container':'panel','information':'tile','metric':'outlined','road_sign':'banner'}[b['role']]
   b.setdefault('style',default);require(b['style'] in STYLES[b['role']],f"Invalid role/style: {b['id']}")
   require(b.get('accent','neutral') in self.palette,f"Unknown accent: {b['id']}")
   require(not ('body' in b and 'body_lines' in b),f"Use body OR body_lines: {b['id']}")
   seen={b['id']};parent=b.get('parent')
   while parent:
    require(parent in self.by_id,f'Unknown parent: {parent}')
    require(parent not in seen,'Containment cycle');seen.add(parent)
    require(self.by_id[parent]['role']=='container','Parent must be a container')
    parent=self.by_id[parent].get('parent')
  if self.mode=='grid':self.place_grid()
  self.validate_geometry()
  self.relationships=self.resolve_relationships()
  self.asset_hashes={}
 def place_aligned_flow(self):
  f=self.c.get('layout',{}).get('aligned_flow')
  if f is None:return
  require(isinstance(f,dict),'aligned_flow must be a mapping')
  require(self.c['layout'].get('mode','absolute')=='absolute','aligned_flow requires absolute mode')
  def number(value,name,minimum=0):
   require(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=minimum,f'Invalid {name}')
   return value
  width=number(self.c['canvas']['width'],'canvas width',1)
  gap=number(f['row_gap'],'row_gap');cw=number(f['card_width'],'card_width',1);ch=number(f['card_height'],'card_height',1)
  gutter=number(f['column_gap'],'column_gap');cols=number(f.get('columns',2),'columns',1)
  require(int(cols)==cols,'columns must be an integer')
  header=number(f['header_height'],'header_height',1);pad=number(f['bottom_padding'],'bottom_padding')
  side=number(f.get('side_padding',pad),'side_padding');boundary_gap=gap-header-pad
  require(boundary_gap>=number(f.get('minimum_boundary_gap',20),'minimum_boundary_gap'),'row_gap must fit header, bottom padding, and minimum boundary gap')
  margin=number(self.c['canvas'].get('safe_margin',70),'safe_margin');top=number(f['top'],'top')
  require(cols*cw+(cols-1)*gutter<=width-2*(margin+side),'Aligned columns exceed padded container width')
  left=(width-(cols*cw+(cols-1)*gutter))/2
  def center(column):
   number(column,'column',1);require(column<=cols,'Column outside aligned flow')
   return left+cw/2+(column-1)*(cw+gutter)
  boxes={b['id']:b for b in self.c['boxes']}
  require(len(boxes)==len(self.c['boxes']),'Duplicate box IDs')
  sections=f.get('sections',[]);require(isinstance(sections,list) and sections,'aligned_flow requires sections')
  used=set();placed=set()
  for section in sections:
   key=section['box'];require(key in boxes and key not in used,'Unknown or duplicate aligned section')
   used.add(key);parent=boxes[key]
   require(parent.get('role')=='container' and not parent.get('parent'),'Aligned sections must be top-level containers')
   rows=number(section['rows'],'section rows',1);require(int(rows)==rows,'Section rows must be an integer')
   height=header+rows*ch+(rows-1)*gap+pad
   parent.update(x=margin,y=top,width=width-2*margin,height=height,header_height=header,padding=side,bottom_padding=pad)
   for b in self.c['boxes']:
    if b.get('parent')!=key:continue
    require(b.get('role')!='container','Aligned-flow nested containers are unsupported; use grid or absolute placement')
    cell=b.get('flow_cell');require(isinstance(cell,dict),'Aligned children require flow_cell')
    row=number(cell['row'],'flow row',1);column=cell['column']
    require(row<=rows and int(row)==row,'Row outside aligned section')
    b.update(x=center(column)-cw/2,y=top+header+(row-1)*(ch+gap),width=cw,height=ch);placed.add(b['id'])
   top+=height+boundary_gap
  require(all('flow_cell' not in b or b['id'] in placed for b in self.c['boxes']),'flow_cell outside declared aligned sections')
  bottom=top-boundary_gap
  self.c.setdefault('footer',{})['y']=bottom+number(f.get('footer_gap',40),'footer_gap')
  self.c['canvas']['height']=math.ceil(self.c['footer']['y']+number(f.get('footer_bottom',70),'footer_bottom',1))
  for bus in self.c.get('buses',[]):
   spec=bus.get('flow_bus')
   if not spec:continue
   require(spec.get('before_box') in placed,'flow_bus target must be an aligned child')
   target=boxes[spec['before_box']];fraction=number(spec.get('gap_fraction',.5),'gap_fraction')
   require(0<fraction<1,'Bus gap_fraction must lie between 0 and 1')
   yy=target['y']-gap*fraction
   require(yy>=0,'Flow bus outside canvas')
   columns=spec.get('columns',[]);require(len(columns)>=2,'flow_bus needs at least two columns')
   bus['points']=[[center(column),yy] for column in columns]
   bus['junctions']=[[center(column),yy] for column in spec.get('junction_columns',[])]
   for r in self.c.get('relationships',[]):
    for end in ['from','to']:
     e=r[end]
     if isinstance(e,dict) and e.get('bus')==bus['id'] and 'column' in e:e['point']=[center(e['column']),yy]
 def find_fonts(self):
  candidates=[Path(self.args.font_dir)] if self.args.font_dir else [Path('/usr/share/fonts/truetype/dejavu'),Path('fonts')]
  for p in candidates:
   files=[p/'DejaVuSans.ttf',p/'DejaVuSans-Bold.ttf']
   if all(f.is_file() for f in files):return files
  raise ValueError('Provide --font-dir containing DejaVuSans.ttf and DejaVuSans-Bold.ttf')
 def px(self,n):return max(1,round(n*self.scale))
 def font(self,n,b=False):
  key=(self.px(n),b)
  if key not in self.fonts:self.fonts[key]=ImageFont.truetype(str(self.font_paths[int(b)]),key[0],layout_engine=ImageFont.Layout.BASIC)
  return self.fonts[key]
 def size(self,name):
  a={'title':112,'subtitle':52,'heading':52,'box':42,'body':38,'metric':80,'label':30,'footer':28}
  b={'title':52,'subtitle':27,'heading':26,'box':32,'body':25,'metric':64,'label':23,'footer':24}
  return (a if self.card else b)[name]
 def text(self,x,y,text,n,color=None,b=False,anchor='lt'):
  self.d.text((round(x),round(y)),str(text),font=self.font(n,b),fill=color or self.t['text'],anchor=anchor)
 def width(self,text,n,b=False):return self.d.textlength(str(text),font=self.font(n,b))
 def wrap(self,text,n,width,b=False):
  lines=[]
  for para in str(text).split('\n'):
   line=''
   for word in para.split():
    require(self.width(word,n,b)<=width,f'Text word exceeds available width: {word}')
    test=(line+' '+word).strip()
    if line and self.width(test,n,b)>width:lines.append(line);line=word
    else:line=test
   lines.append(line)
  return lines
 def colors(self,b):
  p=self.palette[b.get('accent','neutral')];i=0 if self.theme=='dark' else 2
  return p[i],p[i+1]
 def rect(self,b,fill,stroke,r=18,width=3):
  x,y,w,h=[b[k] for k in ['x','y','width','height']]
  self.d.rounded_rectangle((x,y,x+w,y+h),self.px(r),fill,stroke,self.px(width))
 def place_grid(self):
  layout=self.c.get('layout',{});gap=layout.get('gap',32)*self.scale
  row_gap=layout.get('row_gap',gap);column_gap=layout.get('column_gap',gap)
  require(row_gap>=0 and column_gap>=0,'Grid gaps cannot be negative')
  margin=self.c['canvas'].get('safe_margin',80)
  start=self.px(560);end=self.H-self.px(200)
  def group(parent,area,cols):
   children=[b for b in self.boxes if b.get('parent')==parent]
   if not children:return
   x,y,w,h=area;rows=max(b['layout']['row'] for b in children)
   require(isinstance(cols,int) and cols>0,'Grid columns must be positive integers')
   rg=self.by_id[parent].get('layout',{}).get('row_gap',row_gap) if parent else row_gap
   cg=self.by_id[parent].get('layout',{}).get('column_gap',column_gap) if parent else column_gap
   require(rg>=0 and cg>=0,'Grid gaps cannot be negative')
   cellw=(w-cg*(cols-1))/cols
   weights=self.c.get('layout',{}).get('row_weights',[1]*rows) if parent is None else self.by_id[parent].get('layout',{}).get('row_weights',[1]*rows)
   require(len(weights)==rows and all(v>0 for v in weights),'row_weights must have one positive value per grid row')
   heights=[(h-rg*(rows-1))*v/sum(weights) for v in weights]
   for b in children:
    l=b['layout'];r=l['row'];c=l['column'];span=l.get('span',1)
    require(all(isinstance(v,int) for v in [r,c,span]) and r>=1 and c>=1 and span>=1 and c+span-1<=cols,'Grid coordinate out of range')
    b.update(x=round(x+(c-1)*(cellw+cg)),y=round(y+sum(heights[:r-1])+(r-1)*rg),width=round(cellw*span+cg*(span-1)),height=round(heights[r-1]))
    if b['role']=='container':
     pad=b.get('padding',self.px(40));head=b.get('header_height',self.px(160));bottom=b.get('bottom_padding',pad);b['header_height']=head
     group(b['id'],(b['x']+pad,b['y']+head,b['width']-2*pad,b['height']-head-bottom),l.get('child_columns',2))
  group(None,(margin,start,self.W-2*margin,end-start),self.c.get('layout',{}).get('columns',4))
 def validate_geometry(self):
  for b in self.boxes:
   for k in ['x','y','width','height']:require(k in b,f'Missing {k}: {b["id"]}')
   x,y,w,h=[b[k] for k in ['x','y','width','height']]
   for key in ['padding','bottom_padding','header_height']:
    if key in b:require(isinstance(b[key],(int,float)) and math.isfinite(b[key]) and b[key]>=0,f'Invalid {key}: {b["id"]}')
   require(b.get('title_alignment','left') in ['left','center'],'Invalid title_alignment')
   require(w>0 and h>0 and x>=0 and y>=0 and x+w<=self.W and y+h<=self.H,f'Box outside canvas: {b["id"]}')
   if b.get('parent'):
    p=self.by_id[b['parent']];pad=p.get('padding',self.px(40) if self.mode=='grid' else 0);bottom=p.get('bottom_padding',pad)
    require(x>=p['x']+pad and y>=p['y']+p.get('header_height',self.px(90)) and x+w<=p['x']+p['width']-pad and y+h<=p['y']+p['height']-bottom,f'Child outside parent content: {b["id"]}')
   for other in self.boxes:
    if other['id']==b['id'] or other.get('parent')!=b.get('parent'):continue
    if 'x' not in other:continue
    overlap=x<other['x']+other['width'] and x+w>other['x'] and y<other['y']+other['height'] and y+h>other['y']
    require(not overlap or 'z_index' in b or 'z_index' in other,f'Peer overlap: {b["id"]}, {other["id"]}')
 def endpoint(self,e):
  if isinstance(e,str):e={'box':e,'side':'bottom','offset':.5}
  if 'bus' in e:
   require(e['bus'] in self.buses,'Unknown bus endpoint')
   pt=tuple(e['point']);route=self.buses[e['bus']]['points']
   require(any((a[0]==z[0]==pt[0] and min(a[1],z[1])<=pt[1]<=max(a[1],z[1])) or (a[1]==z[1]==pt[1] and min(a[0],z[0])<=pt[0]<=max(a[0],z[0])) for a,z in zip(route,route[1:])), 'Bus endpoint is not on its path')
   return pt
  require(e.get('box') in self.by_id,'Unknown box endpoint')
  b=self.by_id[e['box']];side=e.get('side','bottom');o=e.get('offset',.5)
  require(side in ['left','right','top','bottom'] and 0<=o<=1,'Invalid edge port')
  return (b['x']+(b['width'] if side=='right' else 0 if side=='left' else o*b['width']), b['y']+(b['height'] if side=='bottom' else 0 if side=='top' else o*b['height']))
 def auto_route(self,a,z,endpoints):
  excluded={e.get('box') for e in endpoints if isinstance(e,dict)}
  obstacles=[b for b in self.boxes if b['role']!='container' and b['id'] not in excluded]
  pad=self.px(20)
  def clear(pts):
   for u,v in zip(pts,pts[1:]):
    for b in obstacles:
     x,y,w,h=b['x']-pad,b['y']-pad,b['width']+2*pad,b['height']+2*pad
     if u[0]==v[0] and x<u[0]<x+w and max(u[1],v[1])>y and min(u[1],v[1])<y+h:return False
     if u[1]==v[1] and y<u[1]<y+h and max(u[0],v[0])>x and min(u[0],v[0])<x+w:return False
   return True
  candidates=[[a,(z[0],a[1]),z],[a,(a[0],z[1]),z]]
  for b in obstacles:
   for x in [b['x']-2*pad,b['x']+b['width']+2*pad]:
    if 0<=x<=self.W:candidates.append([a,(x,a[1]),(x,z[1]),z])
   for y in [b['y']-2*pad,b['y']+b['height']+2*pad]:
    if 0<=y<=self.H:candidates.append([a,(a[0],y),(z[0],y),z])
  valid=[p for p in candidates if clear(p)]
  require(valid,'No simple clear automatic route; supply explicit points')
  return min(valid,key=lambda p:sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(p,p[1:])))
 def resolve_relationships(self):
  rels=copy.deepcopy(self.c.get('relationships',[]));ids=set()
  for i,r in enumerate(rels):
   r.setdefault('id',f'line_{i}');require(r['id'] not in ids,'Duplicate relationship ID');ids.add(r['id'])
   a,z=self.endpoint(r['from']),self.endpoint(r['to'])
   if 'points' not in r:r['points']=self.auto_route(a,z,[r['from'],r['to']])
   pts=[tuple(p) for p in r['points']]
   require(pts[0]==a and pts[-1]==z,f'Detached endpoint: {r["id"]}')
   require(all(u[0]==v[0] or u[1]==v[1] for u,v in zip(pts,pts[1:])),f'Non-orthogonal route: {r["id"]}')
  return rels
 def line_style(self,key):
  st=self.c.get('line_styles',{}).get(key)
  require(st is not None,f'Unknown line style: {key}')
  accent=st.get('accent','neutral');fg=self.colors({'accent':accent})[0]
  return (self.t['connector'] if accent=='neutral' else fg),st
 def path(self,points,key,arrows='none'):
  require(arrows in ['start','end','both','none'],'Invalid arrow setting')
  col,st=self.line_style(key);pts=[tuple(p) for p in points]
  require(len(pts)>=2,'Line needs at least two points')
  require(all(0<=x<=self.W and 0<=y<=self.H for x,y in pts),'Line outside canvas')
  width=max(1,round(st.get('width',5)*self.scale))
  if st.get('pattern','solid')=='dashed':
   dash,gap=[v*self.scale for v in st.get('dash',[14,11])];require(dash>0 and gap>=0,'Invalid dash pattern')
   for a,b in zip(pts,pts[1:]):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);pos=0
    while pos<length:
     end=min(pos+dash,length);self.d.line((a[0]+dx*pos/length,a[1]+dy*pos/length,a[0]+dx*end/length,a[1]+dy*end/length),fill=col,width=width);pos+=dash+gap
  else:self.d.line(pts,fill=col,width=width,joint='curve')
  pts=[p for i,p in enumerate(pts) if i==0 or p!=pts[i-1]]
  require(len(pts)>1,'Zero length line')
  def head(a,b):
   angle=math.atan2(b[1]-a[1],b[0]-a[0]);length=self.px(19)
   self.d.polygon([b,(b[0]-length*math.cos(angle-.45),b[1]-length*math.sin(angle-.45)),(b[0]-length*math.cos(angle+.45),b[1]-length*math.sin(angle+.45))],fill=col)
  if arrows in ['end','both']:head(pts[-2],pts[-1])
  if arrows in ['start','both']:head(pts[1],pts[0])
 def label(self,pos,text):
  x,y=pos['x'],pos['y'];n=self.size('label');bb=self.d.textbbox((x,y),text,font=self.font(n),anchor='mm')
  self.d.rounded_rectangle((bb[0]-self.px(10),bb[1]-self.px(7),bb[2]+self.px(10),bb[3]+self.px(7)),self.px(4),fill=self.t['background']);self.text(x,y,text,n,self.t['secondary'],anchor='mm')
 def icon(self,b,cx,cy,size,badge,fg,fill):
  global_cfg=self.c.get('icons',{})
  require(global_cfg.get('provider','google_material_symbols')=='google_material_symbols','Only google_material_symbols is supported')
  if not global_cfg.get('enabled',True) or not b.get('icon'):return
  name=b['icon'];require(re.fullmatch(r'[a-z0-9_]+',name) is not None,'Invalid icon name')
  family=b.get('icon_family',global_cfg.get('family','outlined'))
  local=Path(self.args.icon_dir)/family/(name+'.svg') if self.args.icon_dir else None
  if local and local.is_file():svg=local.read_text()
  else:
   require(family=='outlined' and name in ICON_SVGS,f'Provide local SVG for {family}/{name}')
   require(all(global_cfg.get(k,v)==v for k,v in [('fill',0),('weight',400),('grade',0),('optical_size',48)]),'Variable icon settings require matching local SVG assets')
   svg=ICON_SVGS[name]
  self.asset_hashes[family+'/'+name]=hashlib.sha256(svg.encode()).hexdigest()
  if b.get('icon_treatment',global_cfg.get('treatment','circle'))=='circle':self.d.ellipse((cx-badge/2,cy-badge/2,cx+badge/2,cy+badge/2),fill=blend(fg,fill,.2))
  tree=ET.fromstring(svg)
  for el in tree.iter():
   if el.tag.split('}')[-1] in ['path','circle','rect','polygon','polyline','ellipse'] and el.get('fill')!='none':el.set('fill',fg)
  raster=cairosvg.svg2png(bytestring=ET.tostring(tree),output_width=size,output_height=size)
  icon=Image.open(io.BytesIO(raster)).convert('RGBA');self.im.paste(icon,(round(cx-size/2),round(cy-size/2)),icon)
 def box(self,b):
  x,y,w,h=[b[k] for k in ['x','y','width','height']];fg,fill=self.colors(b)
  if b['role']=='container':
   self.rect(b,self.t['surface'],self.t['border'],20,2)
   align=b.get('title_alignment','center' if self.mode=='absolute' else 'left');n=self.size('heading');pad=b.get('padding',self.px(40))
   self.text(x+w/2 if align=='center' else x+pad+(self.px(80) if b.get('icon') else 0),y+self.px(22),b.get('title',''),n,fg,True,'mt' if align=='center' else 'lt')
   if b.get('subtitle'):self.text(x+pad,y+self.px(90),b['subtitle'],self.size('body'),self.t['secondary'])
   if b.get('icon'):self.icon(b,x+pad+self.px(24),y+self.px(48),self.px(48),self.px(64),fg,fill)
   return
  stroke=blend(fg,fill,.5 if self.theme=='dark' else .4)
  direction=b.get('direction','none');require(direction in ['none','right','left','up','down'],'Invalid road sign direction')
  if b['style']=='chevron':
   require(direction!='none','Chevron style requires direction')
   local=[(0,0),(w-self.px(40),0),(w,h/2),(w-self.px(40),h),(0,h)]
   if direction=='left':local=[(w-a,z) for a,z in local]
   elif direction in ['up','down']:
    local=[(0,0),(w,0),(w,h-self.px(40)),(w/2,h),(0,h-self.px(40))]
    if direction=='up':local=[(a,h-z) for a,z in local]
   self.d.polygon([(x+a,y+z) for a,z in local],fill=fill,outline=stroke,width=self.px(3))
  else:self.rect(b,fill,stroke,32 if self.card else 18)
  pad=b.get('padding',self.px(24 if not self.card else 32));require(2*pad<w and 2*pad<h,'Padding consumes box content area');title_n=self.size('box');body_n=self.size('body')
  title=b.get('title','');has_icon=self.c.get('icons',{}).get('enabled',True) and bool(b.get('icon'))
  placement=b.get('icon_placement','left' if b['role']=='road_sign' else 'top_center' if b['style']=='tile' else 'top_right')
  size=self.px(72 if self.card and b['style']=='tile' else 48);badge=self.px(144 if self.card and b['style']=='tile' else 80)
  top=y+pad;left=x+pad;right=x+w-pad;center=False
  if has_icon:
   cx=x+w-pad-badge/2;cy=y+pad+badge/2
   if placement in ['left','header_left','top_left']:
    cx=x+pad+badge/2;cy=y+h/2 if placement=='left' else cy;left=x+2*pad+badge
   elif placement=='top_center':cx=x+w/2;top=y+pad+badge+self.px(22);center=True
   else:right=x+w-2*pad-badge
   self.icon(b,cx,cy,size,badge,fg,fill)
  if b['style']=='tile':center=True
  if 'title_alignment' in b:center=b['title_alignment']=='center'
  if b['role']=='road_sign':
   right=x+w-pad-(self.px(60) if direction!='none' else 0)
   if b['style']=='banner' and direction!='none':
    cx=x+w-self.px(55) if direction=='right' else x+self.px(20) if direction=='left' else x+w/2
    cy=y+self.px(20) if direction=='up' else y+h-self.px(20) if direction=='down' else y+h/2
    v=self.px(12);pts={'right':[(cx-v,cy-v),(cx,cy),(cx-v,cy+v)],'left':[(cx+v,cy-v),(cx,cy),(cx+v,cy+v)],'up':[(cx-v,cy+v),(cx,cy),(cx+v,cy+v)],'down':[(cx-v,cy-v),(cx,cy),(cx+v,cy-v)]}[direction]
    self.d.line(pts,fill=fg,width=self.px(4))
  if b['role']=='metric':
   require('value' in b,'Metric requires a supplied value')
   self.text(left,top,b['value'],self.size('metric'),fg,True)
   vw=self.width(b['value'],self.size('metric'),True)
   if b.get('unit'):self.text(left+vw+self.px(14),top+self.px(35),b['unit'],body_n,self.t['secondary'])
   top+=self.px(80)
  title_width=right-left
  lines=self.wrap(title,title_n,title_width,True)
  for t in lines:
   require(top+self.px(title_n)<=y+h-pad,f'Title overflows box: {b["id"]}')
   self.text((left+right)/2 if center else left,top,t,title_n,b=True,anchor='mt' if center else 'lt');top+=self.px(title_n+8)
  top+=self.px(12)
  body_width=x+w-pad-left
  if has_icon and placement in ['top_right','top_left','header_left'] and top<y+pad+badge:body_width=min(body_width,right-left)
  body=b.get('body_lines')
  if body is None:body=self.wrap(b['body'],body_n,body_width) if b.get('body') else []
  for t in body:
   require(self.width(t,body_n)<=body_width,f'Body line too wide: {b["id"]}')
   require(top+self.px(body_n)<=y+h-pad,f'Text overflows box: {b["id"]}; enlarge box or shorten copy')
   self.text((left+right)/2 if center else left,top,t,body_n,self.t['secondary'],anchor='mt' if center else 'lt');top+=self.px(body_n+9)
 def render(self):
  pos=self.c.get('title_position',{'x':self.px(80),'y':self.px(55)})
  title_n=self.size('title');subtitle_n=self.size('subtitle')
  lines=self.wrap(self.c.get('title',''),title_n,self.W-2*pos['x'],True)
  for i,t in enumerate(lines):self.text(pos['x'],pos['y']+i*self.px(title_n+10),t,title_n,b=True)
  sp=self.c.get('subtitle_position',{'x':pos['x'],'y':pos['y']+len(lines)*self.px(title_n+10)+self.px(16)})
  for i,t in enumerate(self.wrap(self.c.get('subtitle',''),subtitle_n,self.W-2*sp['x'])):self.text(sp['x'],sp['y']+i*self.px(subtitle_n+12),t,subtitle_n,self.t['secondary'])
  def depth(b):return 1+depth(self.by_id[b['parent']]) if b.get('parent') else 0
  for b in sorted([b for b in self.boxes if b['role']=='container'],key=depth):self.box(b)
  if self.c.get('layout',{}).get('connectors',False):
   for b in self.buses.values():self.path(b['points'],b['line_style'])
   for r in self.relationships:self.path(r['points'],r['line_style'],r.get('arrows','end'))
  for b in sorted([b for b in self.boxes if b['role']!='container'],key=lambda b:b.get('z_index',0)):self.box(b)
  if self.c.get('layout',{}).get('connectors',False):
   for b in self.buses.values():
    for x,y in b.get('junctions',[]):
     rad=self.px(6);self.d.ellipse((x-rad,y-rad,x+rad,y+rad),fill=self.line_style(b['line_style'])[0])
    if b.get('label'):self.label(b['label_position'],b['label'])
   for r in self.relationships:
    if r.get('label'):self.label(r.get('label_position',{'x':sum(p[0] for p in r['points'])/len(r['points']),'y':sum(p[1] for p in r['points'])/len(r['points'])}),r['label'])
  if self.c.get('legend'):
   l=self.c['legend'];x,y=l['x'],l['y'];self.text(x,y,'CONNECTION LEGEND',25,b=True)
   for i,e in enumerate(l['entries']):
    yy=y+self.px(70+i*65);self.path([[x,yy+self.px(12)],[x+self.px(110),yy+self.px(12)]],e['line_style']);self.text(x+self.px(135),yy,e['label'],25)
  f=self.c.get('footer',{})
  if self.mode=='grid':
   x=self.W/2;y=self.H-self.px(130);anchor='mt'
  else:x=f.get('x',self.px(80));y=f.get('y',self.H-self.px(100));anchor='lt'
  if f.get('brand'):self.text(x,y,f['brand'],self.size('footer'),b=True,anchor=anchor)
  if f.get('note'):self.text(x,y+self.px(42),f['note'],self.size('footer'),self.t['secondary'],anchor=anchor)
  return self.im

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('input',type=Path);p.add_argument('--preset',default='ecosystem')
 p.add_argument('--theme',choices=['dark','light']);p.add_argument('--output',type=Path,default=Path('infographic.png'))
 p.add_argument('--font-dir');p.add_argument('--icon-dir',help='Offline SVGs in FAMILY/NAME.svg subfolders')
 args=p.parse_args();cfg=load(args.input,args.preset);renderer=Renderer(cfg,args);im=renderer.render()
 args.output.parent.mkdir(parents=True,exist_ok=True);im.save(args.output,format='PNG',optimize=False,compress_level=9)
 manifest={'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),'preset':args.preset,'theme':renderer.theme,'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'fonts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in renderer.font_paths},'icons':renderer.asset_hashes,'versions':{'python':sys.version.split()[0],'pillow':Image.__version__,'pyyaml':yaml.__version__,'cairosvg':cairosvg.__version__}}
 args.output.with_suffix('.render.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(args.output.resolve())

if __name__=='__main__':
 try:main()
 except (ValueError,KeyError,TypeError) as exc:raise SystemExit('Configuration error: '+str(exc))
