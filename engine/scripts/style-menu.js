const token=location.hash.slice(1)||sessionStorage.getItem('diy-style-token')||'';
const state={regions:[],styles:[],colors:[],patterns:[],choices:{},saved:{},active:null,epoch:0,urls:[],busy:false,closed:false,loaded:false};
sessionStorage.setItem('diy-style-token',token);history.replaceState(null,'',location.pathname);
const $=id=>document.getElementById(id),clone=x=>JSON.parse(JSON.stringify(x));
async function api(path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),['/api/save','/api/photo'].includes(path)?60000:12000);try{const r=await fetch(path,{method:body===undefined?'GET':'POST',signal:controller.signal,headers:{'X-DIY-Token':token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok){let e=await r.json();throw Error(e.message)}return r;}catch(e){if(e.name==='AbortError'||e instanceof TypeError){$('retry').hidden=false;throw Error('本地菜单服务未连接。请先点击“重新连接”；仍失败时，请在 DSH 设置 → DIY 手账本中重新打开样式菜单。')}throw e}finally{clearTimeout(timer)}}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error)}
function dirty(){return !!state.photoDirty||JSON.stringify(state.choices)!==JSON.stringify(state.saved)}
function photoControls(){
 const r=state.regions.find(r=>r.id===state.active),c=state.choices[state.active];
 $('pick-first').textContent=c.style===8?'选择左侧图片':'选择图片';$('pick-second').hidden=c.style!==8;
 $('pick-second').disabled=state.busy||!r.photo;
}
function setBusy(value){state.busy=value;for(const input of document.querySelectorAll('button,input,select'))input.disabled=value;photoControls();pairControls()}
function pickPhoto(index){state.importIndex=index;$('photo-file').value='';$('photo-file').click()}
$('pick-first').onclick=()=>pickPhoto(0);$('pick-second').onclick=()=>pickPhoto(1);
async function importPhoto(payload,id=state.active){
 setBusy(true);status('正在读取图片并更新预览…');
 try{const data=await (await api('/api/photo',{slot:id,...payload})).json();const r=state.regions.find(r=>r.id===id);r.photos=data.photos;r.photo=data.photo;state.photoDirty=true;
  if(r.photo&&state.choices[id].style===0)state.choices[id].style=1;
  show(id);status('图片已选好并更新预览。点击“保存并应用”后更新皮肤。');
 }catch(e){status(e.message,true)}finally{setBusy(false);nav()}
}
$('photo-file').onchange=async e=>{
 const file=e.target.files[0];if(!file)return;
 if(file.size>20*1024*1024){status('单张图片不能超过 20 MB。',true);return}
 const id=state.active,c=state.choices[id],index=c.style===8&&c.swapPhotos?1-state.importIndex:state.importIndex;setBusy(true);
 try{const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(Error('无法读取这张图片。'));r.readAsDataURL(file)});await importPhoto({index,name:file.name,data},id)}catch(e){setBusy(false);status(e.message,true)}
};
$('use-folder').onclick=()=>importPhoto({mode:'folder'});
function adjusted(){return state.choices[state.active].photoAdjustments[state.photoIndex||0]}
function adjustmentValue(key){const c=state.choices[state.active],r=state.regions.find(r=>r.id===state.active);return adjusted()[key]??r.layoutGeometry[c.style].angles[state.photoIndex||0]}
function syncPosition(){for(const key of ['x','y','angle','scale'])for(const input of document.querySelectorAll('[data-position="'+key+'"]'))input.value=adjustmentValue(key)}
function queuePositionPreview(){if(!state.positionTimer)state.positionTimer=setTimeout(()=>{state.positionTimer=null;previewImages(true)},140)}
function updatePosition(key,value){
 const limit=key==='scale'?250:key==='angle'?30:50,min=key==='scale'?25:-limit;if(!Number.isFinite(value))return;
 adjusted()[key]=Math.round(Math.max(min,Math.min(limit,value))*10)/10;
 syncPosition();nav();queuePositionPreview();status('位置、角度与缩放已暂存，点击“保存并应用”后生效。');
}
function positionControls(){
 const c=state.choices[state.active];$('position-panel').hidden=c.style===0;
 if(c.style===0)return;
 const r=state.regions.find(r=>r.id===state.active);
 syncCanvasPreview();
 if(c.style!==8)state.photoIndex=0;
 state.photoIndex=state.photoIndex||0;$('position-targets').replaceChildren();
 for(let i=0;i<(c.style===8?2:1);i++){
  const label=document.createElement('label');label.className='swatch';const input=document.createElement('input');input.type='radio';input.name='position-target';input.checked=state.photoIndex===i;input.disabled=state.busy;
  const text=document.createElement('span');text.textContent=c.style===8?(i===0?'照片 1（原左侧）':'照片 2（原右侧）'):'当前照片';label.append(input,text);input.onchange=()=>{state.photoIndex=i;positionControls()};$('position-targets').append(label);
 }
 $('position-controls').replaceChildren();
 for(const [key,title,limit] of [['x','左右位置（%）',50],['y','上下位置（%）',50],['angle','倾斜角度（°）',30],['scale','缩放（%）',250]]){
  const row=document.createElement('div');row.className='position-row';const label=document.createElement('label');label.htmlFor='position-'+key;label.textContent=title;row.append(label);
  for(const type of ['range','number']){const input=document.createElement('input');input.type=type;input.min=key==='scale'?25:-limit;input.max=limit;input.step=key==='scale'?'1':'0.1';input.dataset.position=key;input.value=adjustmentValue(key);input.disabled=state.busy;if(type==='range')input.id='position-'+key;input.setAttribute('aria-label',title+(type==='number'?'数值':''));
   const commit=()=>{if(input.value===''||!Number.isFinite(input.valueAsNumber)){syncPosition();return}updatePosition(key,input.valueAsNumber)};
   if(type==='range'){input.oninput=commit;input.onchange=commit}
   else{input.onblur=commit;input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();commit()}}}
   row.append(input)}
  $('position-controls').append(row);
 }
 $('position-help').textContent=(c.style===8?'正在调整照片 '+((state.photoIndex||0)+1)+'。':'')+'虚线框为实际画布边界。拖动调整位置；方向键可微调。';syncCanvasPreview();
}
$('position-reset').onclick=()=>{state.choices[state.active].photoAdjustments[state.photoIndex||0]={x:0,y:0,angle:null,scale:100};positionControls();nav();previewImages();status('当前照片已恢复布局默认位置、角度与大小。保存后生效。')};
$('position-preview').onpointerdown=e=>{
 if(state.busy||state.closed||e.button!==0)return;
 const c=state.choices[state.active],r=state.regions.find(r=>r.id===state.active),g=r.layoutGeometry[c.style],rect=e.currentTarget.getBoundingClientRect();
 const outer=Math.min(rect.width/r.canvasSize[0],rect.height/r.canvasSize[1]),scale=outer*Math.min(r.canvasSize[0]/g.width,r.canvasSize[1]/g.height);
 state.drag={id:e.pointerId,x:e.clientX,y:e.clientY,start:clone(adjusted()),width:r.id==='home'?rect.width:g.width*scale,height:r.id==='home'?rect.height:g.height*scale};e.currentTarget.setPointerCapture(e.pointerId);e.currentTarget.focus();e.preventDefault();
};
$('position-preview').onpointermove=e=>{const d=state.drag;if(!d||d.id!==e.pointerId)return;updatePosition('x',d.start.x+(e.clientX-d.x)/d.width*100);updatePosition('y',d.start.y+(e.clientY-d.y)/d.height*100)};
function endDrag(e){if(!state.drag)return;state.drag=null;if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId)}
$('position-preview').onpointerup=endDrag;$('position-preview').onpointercancel=endDrag;$('position-preview').onlostpointercapture=()=>{state.drag=null};
$('position-preview').onkeydown=e=>{if(state.busy||state.closed)return;const map={ArrowLeft:['x',-1],ArrowRight:['x',1],ArrowUp:['y',-1],ArrowDown:['y',1]};if(map[e.key]){e.preventDefault();const [key,delta]=map[e.key];updatePosition(key,adjusted()[key]+delta*(e.shiftKey?5:1))}};
function nav(){
 $('regions').replaceChildren();
 for(const r of state.regions){const b=document.createElement('button');b.className=r.id===state.active?'active':'';b.disabled=state.busy;const n=document.createElement('span');n.textContent=r.name;const t=document.createElement('small');t.textContent='样式 '+state.choices[r.id].style+(JSON.stringify(state.choices[r.id])!==JSON.stringify(state.saved[r.id])?' · 未保存':'');b.append(n,t);b.onclick=()=>show(r.id);$('regions').append(b)}
}
function sceneControls(){
 const r=state.regions.find(x=>x.id===state.active);const main=['home','main-sidebar'].includes(r.id);
 if(!main&&r.id!=='settings-sidebar')state.scenePage=r.id;
 state.scenePage=state.scenePage||'general';$('scene-page-row').hidden=r.id!=='settings-sidebar';
 $('scene-page').replaceChildren();for(const item of state.regions.filter(x=>x.id!=='home'&&!x.id.endsWith('sidebar'))){const o=document.createElement('option');o.value=item.id;o.textContent=item.name.replace('设置-','');o.selected=item.id===state.scenePage;$('scene-page').append(o)}
 $('preview-description').textContent=(main?'主界面（含主界面左栏）':'设置 · '+state.regions.find(x=>x.id===state.scenePage).name.replace('设置-',''))+' · 使用当前所有未保存选择';
}
function sceneSize(){return $('scene-viewport').value==='wide'?[1920,1080]:[1200,840]}
function fitScene(){const width=$('scene-stage').clientWidth,[w,h]=sceneSize();const scale=state.sceneZoom?width/w:Math.min(width/w,Math.max(280,window.innerHeight-280)/h);$('scene-frame').style.width=w+'px';$('scene-frame').style.height=h+'px';$('scene-frame').style.transform='scale('+scale+')';$('scene-frame').style.left=((width-w*scale)/2)+'px';$('scene-stage').style.height=(h*scale)+'px'}
function syncCanvasPreview(){
 const r=state.regions.find(r=>r.id===state.active);if(!r)return;
 const home=r.id==='home',size=home?(state.homeCanvasSize||[890,690]):r.canvasSize;
 for(const img of document.querySelectorAll('#position-preview,#selected-preview,.card img')){
  img.style.objectFit=home?'fill':'';
  img.style.aspectRatio=(home||img.id==='position-preview')?size.join(' / '):'';
  img.style.height=home?'auto':'';
 }
 if(home)$('position-help').textContent='画布随主界面可用区域伸展；照片等比填满相框。拖动调整位置，方向键可微调。';
}
$('scene-zoom').onclick=()=>{state.sceneZoom=!state.sceneZoom;$('scene-zoom').textContent=state.sceneZoom?'适应窗口':'放大预览';fitScene()};
window.addEventListener('resize',fitScene);
new ResizeObserver(fitScene).observe($('scene-stage'));
function scenePreview(){
 clearTimeout(state.sceneTimer);const epoch=(state.sceneEpoch||0)+1;state.sceneEpoch=epoch;
 $('live-preview').hidden=false;sceneControls();$('preview-progress').hidden=false;$('preview-progress').textContent='正在生成界面场景…';$('scene-stage').hidden=true;
 const payload={active:state.active,settingsPage:state.scenePage,choices:clone(state.choices),viewport:sceneSize()};
 state.sceneTimer=setTimeout(async()=>{try{const markup=await (await api('/api/scene',payload)).text();if(epoch!==state.sceneEpoch)return;
  const frame=$('scene-frame');frame.onload=()=>{if(epoch!==state.sceneEpoch)return;$('preview-progress').hidden=true;$('scene-stage').hidden=false;fitScene();
   const chat=frame.contentDocument.querySelector('[data-conversation-region="chat"]');
   if(chat){const s=frame.contentWindow.getComputedStyle(chat,'::before'),w=parseFloat(s.width),h=parseFloat(s.height);if(w>0&&h>0)state.homeCanvasSize=[w,h];}
   syncCanvasPreview();
  };frame.srcdoc=markup;
 }catch(e){if(epoch!==state.sceneEpoch)return;$('preview-progress').textContent='场景生成失败：'+e.message;status(e.message,true)}},160);
}
$('scene-page').onchange=()=>{state.scenePage=$('scene-page').value;scenePreview()};
$('scene-viewport').onchange=scenePreview;
$('scene-refresh').onclick=scenePreview;
function previewImages(onlySelected=false){
 const epoch=++state.epoch;state.urls.forEach(URL.revokeObjectURL);state.urls=[];scenePreview();
 const c=clone(state.choices[state.active]),region=state.regions.find(x=>x.id===state.active),groups=new Map();
 for(const img of document.querySelectorAll('.card img'))if(!onlySelected||Number(img.parentElement.dataset.style)===c.style)groups.set(Number(img.parentElement.dataset.style),[img]);
 groups.get(c.style).push($('selected-preview'),$('position-preview'));
 for(const [style,images] of groups){const q=new URLSearchParams({slot:state.active,style,color1:c.tapeColors[0],color2:c.tapeColors[1],pattern1:c.tapePatterns[0],pattern2:c.tapePatterns[1],swap:c.swapPhotos?1:0,adjustments:JSON.stringify(c.photoAdjustments),borders:JSON.stringify(c.photoBorders),front:c.frontPhoto});
  api('/api/preview?'+q).then(r=>r.blob()).then(async blob=>{if(epoch!==state.epoch)return;const url=URL.createObjectURL(blob);state.urls.push(url);for(const img of images)img.src=url;}).catch(e=>{if(epoch===state.epoch){status(e.message,true);if(style===c.style){$('preview-progress').textContent='预览生成失败：'+e.message;$('preview-progress').hidden=false}}})
 }
}
function pairControls(){
 const r=state.regions.find(x=>x.id===state.active),c=state.choices[state.active];
 $('pair-panel').hidden=c.style!==8;
 $('layer-swap').textContent='⇅ '+(c.frontPhoto==='left'?'左侧照片在前':'右侧照片在前')+' · 调换';$('layer-swap').disabled=state.busy;
 $('swap').disabled=state.busy||r.photos.length<2;
 const p=c.swapPhotos?[...r.photos].reverse():r.photos;
 $('pair-note').textContent=p.length>1?'左侧：'+p[0]+' · 右侧：'+p[1]+'。调换仅改变照片顺序，胶带纹样与颜色保持在原相框。':p.length===1?'只有一张图片，两个相框均使用 '+p[0]+'。添加第二张图片后重新打开菜单即可调换。':'暂无图片，显示示意图。放入两张图片后可调换。';
}
$('layer-swap').onclick=()=>{const c=state.choices[state.active];c.frontPhoto=c.frontPhoto==='left'?'right':'left';pairControls();nav();previewImages();status('照片前后层级已调换，位置与选图保持不变。保存后生效。')};
$('swap').onclick=()=>{const c=state.choices[state.active];c.swapPhotos=!c.swapPhotos;pairControls();nav();previewImages();status('双照片顺序已调换，点击“保存并应用”后生效。')};
function colors(){
 pairControls();positionControls();
 const r=state.regions.find(x=>x.id===state.active),c=state.choices[state.active],count=r.tapeCounts[c.style];
 $('color-panel').hidden=count===0;$('color-options').replaceChildren();
 $('color-note').textContent=count===1?'当前布局使用一条胶带。第二组纹样与颜色会保留，双胶带时再显示。':(c.style===8?'两组纹样与颜色分别用于左、右相框的胶带。':'两条胶带可分别选择纹样与颜色。');
 for(let i=0;i<count;i++){
  const field=document.createElement('fieldset');field.dataset.tape=i+1;const legend=document.createElement('legend');legend.textContent=count===1?'胶带':(c.style===8?(i===0?'左侧相框胶带':'右侧相框胶带'):'胶带 '+(i+1));field.append(legend);
  const patternLabel=document.createElement('p');patternLabel.className='tape-label';patternLabel.textContent='纹样';field.append(patternLabel);
  const patternRow=document.createElement('div');patternRow.className='swatches pattern-options';
  for(const p of state.patterns){const label=document.createElement('label');label.className='swatch';const input=document.createElement('input');input.type='radio';input.name='pattern-'+i;input.value=p.id;input.checked=c.tapePatterns[i]===p.id;input.disabled=state.busy;
   const paint=document.createElement('span');paint.className='paint pattern-'+p.id;paint.style.setProperty('--tape-base','#d2edf4');paint.style.setProperty('--tape-ink','#6db4d2');const text=document.createElement('span');text.textContent=p.name;label.append(input,paint,text);
   input.onchange=()=>{state.choices[state.active].tapePatterns[i]=p.id;nav();previewImages();status('胶带纹样已暂存，布局与颜色保持不变。保存后生效。')};patternRow.append(label)}
  field.append(patternRow);const colorLabel=document.createElement('p');colorLabel.className='tape-label';colorLabel.textContent='颜色';field.append(colorLabel);
  const row=document.createElement('div');row.className='swatches';
  for(const p of state.colors){const label=document.createElement('label');label.className='swatch';const input=document.createElement('input');input.type='radio';input.name='tape-'+i;input.value=p.id;input.checked=c.tapeColors[i]===p.id;input.disabled=state.busy;
   const paint=document.createElement('span');paint.className='paint pattern-solid';paint.style.setProperty('--tape-base',p.base);paint.style.setProperty('--tape-ink',p.ink);const text=document.createElement('span');text.textContent=p.name;label.append(input,paint,text);
   input.onchange=()=>{state.choices[state.active].tapeColors[i]=p.id;nav();previewImages();status('胶带颜色已暂存，布局保持不变。点击“保存并应用”后生效。')};row.append(label)}
  field.append(row);$('color-options').append(field)
 }
}
function choose(id){state.choices[state.active].style=id;show(state.active);status('结构已选择，位置、角度、缩放与胶带设置保持不变。保存后生效。')}
function borderControls(){
 const c=state.choices[state.active];$('border-panel').hidden=c.style===0||c.style===10;$('border-options').replaceChildren();
 for(let i=0;i<(c.style===8?2:1);i++){
  const option=c.photoBorders[i],field=document.createElement('fieldset'),legend=document.createElement('legend');legend.textContent=c.style===8?(i===0?'左侧照片白边':'右侧照片白边'):'照片白边';field.append(legend);
  const row=document.createElement('div');row.className='swatches';
  for(const [value,title] of [['narrow','窄白边'],['wide','宽白边']]){
   const label=document.createElement('label'),input=document.createElement('input');label.className='swatch';input.type='radio';input.name='border-'+i;input.value=value;input.checked=option.width===value;input.disabled=state.busy;input.setAttribute('aria-label',legend.textContent+' · '+title);label.append(input,document.createTextNode(title));row.append(label);
   input.onchange=()=>{option.width=value;borderControls();nav();previewImages();status('白边已更新预览，保存后生效。')};
  }
  field.append(row);
  if(option.width==='wide'){
   const label=document.createElement('label'),toggle=document.createElement('input');label.className='swatch';label.style.marginTop='12px';toggle.type='checkbox';toggle.checked=option.write;toggle.disabled=state.busy;toggle.setAttribute('aria-label',legend.textContent+' · 在宽白边上写字');label.append(toggle,document.createTextNode('在宽白边上写字'));field.append(label);
   const text=document.createElement('input');text.type='text';text.maxLength=40;text.value=option.text;text.placeholder='写一句话或日期（最多 40 字）';text.className='caption-input';text.hidden=!option.write;text.disabled=state.busy;text.setAttribute('aria-label',legend.textContent+' · 题字内容');field.append(text);
   toggle.onchange=()=>{option.write=toggle.checked;text.hidden=!option.write;nav();previewImages()};
   text.oninput=()=>{option.text=text.value;nav();queuePositionPreview();status('题字已更新预览，保存后生效。')};
  }
  $('border-options').append(field);
 }
}
function show(id){
 state.active=id;nav();const r=state.regions.find(x=>x.id===id);$('heading').textContent=r.name;$('photo').textContent=r.photo?'当前首图：'+r.photo+' · 预览使用这张照片':'此文件夹没有照片，以下为样式示意。保存不会添加示意图；无照片时仍隐藏照片、白边与胶带。';$('cards').replaceChildren();
 for(const s of state.styles.filter(s=>r.allowedStyles.includes(s.id)&&(!s.retired||s.id===state.choices[id].style))){const b=document.createElement('button');b.type='button';b.className='card'+(s.id===state.choices[id].style?' selected':'');b.dataset.style=s.id;b.setAttribute('aria-pressed',String(s.id===state.choices[id].style));b.disabled=state.busy;const img=document.createElement('img');img.alt=s.name+'预览';const title=document.createElement('strong');title.textContent=(s.retired?'已保存的旧布局 · ':'')+'样式 '+s.id+' · '+s.name;const desc=document.createElement('span');desc.textContent=s.description;b.append(img,title,desc);b.onclick=()=>choose(s.id);$('cards').append(b)}
 photoControls();borderControls();colors();previewImages();
}
$('reset').onclick=()=>{for(const r of state.regions)state.choices[r.id].style=1;show(state.active);status('全部区域已选样式 1，胶带纹样与颜色未改变。保存后生效。')};
$('save').onclick=async()=>{state.busy=true;for(const b of document.querySelectorAll('button,input'))b.disabled=true;status('正在保存布局与胶带设置…');try{const res=await (await api('/api/save',state.choices)).json();if(res.ok||res.saved){state.saved=clone(state.choices);state.photoDirty=false;}status(res.message,!res.ok)}catch(e){status(e.message,true)}finally{state.busy=false;for(const b of document.querySelectorAll('button,input'))b.disabled=false;nav();pairControls();photoControls()}};
$('close').onclick=async()=>{if(dirty()&&!confirm('还有未保存的选择，确定关闭吗？'))return;try{await api('/api/close',{});state.closed=true;state.saved=clone(state.choices);status('菜单已关闭。再次使用请在 DSH 设置 → DIY 手账本中打开样式菜单。');for(const b of document.querySelectorAll('button,input'))b.disabled=true}catch(e){status(e.message,true)}};
window.addEventListener('beforeunload',e=>{if(dirty()){e.preventDefault();e.returnValue=''}});
async function connect(){try{
 if(state.loaded){await api('/api/ping');$('retry').hidden=true;status('连接已恢复，未保存的选择仍保留。');return}
 $('heading').textContent='正在读取样式…';const data=await (await api('/api/state')).json();state.regions=data.regions;state.styles=data.styles;state.colors=data.colors;state.patterns=data.patterns;
 state.choices=Object.fromEntries(data.regions.map(r=>[r.id,{style:r.style,tapeColors:[...r.tapeColors],tapePatterns:[...r.tapePatterns],photoAdjustments:clone(r.photoAdjustments),photoBorders:clone(r.photoBorders),swapPhotos:r.swapPhotos||false,frontPhoto:r.frontPhoto||'right'}]));state.saved=clone(state.choices);state.loaded=true;$('save').disabled=false;$('reset').disabled=false;$('retry').hidden=true;status('先选上方布局，再选下方每条胶带的纹样与颜色。');show(state.regions[0].id)
}catch(e){if(!state.loaded)$('heading').textContent='菜单服务未连接';$('retry').hidden=false;status(e.message,true)}}
$('retry').onclick=()=>connect().then(()=>{if(state.loaded)previewImages()});
setInterval(()=>{if(!state.closed&&!document.hidden)api('/api/ping').catch(e=>status(e.message,true))},45000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!state.closed)connect()});connect();
