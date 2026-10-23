// Shared by the menu, scene previews and the integrated plugin. No user scripts.
function createJournalVideoRenderer(win = window, assetBase = '/api/skin-center/v2/skins/diy-journal/assets/') {
  const doc=win.document, svgNS='http://www.w3.org/2000/svg', htmlNS='http://www.w3.org/1999/xhtml';
  const reduced=win.matchMedia('(prefers-reduced-motion: reduce)'), media=new Map(), cleanups=new Set();
  let disposed=false, serial=0;
  function asset(ref) {
    if(!/^diy-media\/[a-f0-9]{64}\.mp4$/.test(ref))throw Error('Invalid journal video');
    return assetBase+ref;
  }
  function blob(ref) {
    if(!media.has(ref)){
      const controller=new win.AbortController(), item={controller,url:null};
      item.promise=win.fetch(asset(ref),{signal:controller.signal,credentials:'same-origin'}).then(r=>{
        if(!r.ok)throw Error('Video unavailable');return r.blob();
      }).then(data=>{if(disposed)throw Error('Disposed');item.url=win.URL.createObjectURL(data);return item.url});
      media.set(ref,item);
    }
    return media.get(ref).promise;
  }
  function mount(host, text) {
    const parsed=new win.DOMParser().parseFromString(text,'image/svg+xml');
    if(parsed.querySelector('parsererror')||parsed.documentElement.localName!=='svg')throw Error('Invalid photo layout');
    // Layouts are generated locally, but still never insert executable SVG content.
    const allowed=new Set(['svg','g','defs','rect','path','circle','ellipse','line','polyline','polygon','image','text','tspan','desc','title','pattern','clipPath','mask','linearGradient','radialGradient','stop','filter','feDropShadow','feGaussianBlur','feOffset','feFlood','feComposite','feMerge','feMergeNode']);
    const elements=[parsed.documentElement,...parsed.documentElement.querySelectorAll('*')];
    for(const el of elements){
      if(el.namespaceURI!==svgNS||!allowed.has(el.localName))throw Error('Unsafe photo layout');
      for(const a of [...el.attributes]){
        if(/^on/i.test(a.name)||/@import|javascript:|https?:|file:/i.test(a.value)&&!a.name.startsWith('xmlns'))throw Error('Unsafe photo attribute');
        if(a.localName==='href'&&!a.value.startsWith('#')&&!/^data:image\/(png|jpeg|webp|gif|bmp|svg\+xml);base64,/.test(a.value))throw Error('Unsafe image');
        if(/url\(/i.test(a.value)&&/url\(\s*['"]?(?!#)/i.test(a.value))throw Error('Unsafe paint');
      }
    }
    const svg=doc.importNode(parsed.documentElement,true), prefix='diy-v-'+(++serial)+'-'+Math.random().toString(36).slice(2)+'-';
    const ids=new Map([...svg.querySelectorAll('[id]')].map(el=>[el.id,prefix+el.id]));
    for(const el of [svg,...svg.querySelectorAll('*')])for(const a of [...el.attributes]){
      if(a.name==='id'&&ids.has(a.value))el.setAttribute(a.name,ids.get(a.value));
      else {let value=a.value;for(const [id,next] of ids){value=value.replaceAll('url(#'+id+')','url(#'+next+')');if(value==='#'+id)value='#'+next;}if(value!==a.value)el.setAttribute(a.name,value);}
    }
    svg.style.cssText='display:block;width:100%;height:100%;pointer-events:none;overflow:hidden';
    host.replaceChildren(svg);
    const videos=[];
    for(const image of svg.querySelectorAll('image[data-diy-video]')){
      const ref=image.getAttribute('data-diy-video');asset(ref);
      const foreign=doc.createElementNS(svgNS,'foreignObject');
      for(const key of ['x','y','width','height','transform','clip-path','opacity'])if(image.hasAttribute(key))foreign.setAttribute(key,image.getAttribute(key));
      const video=doc.createElementNS(htmlNS,'video');video.muted=true;video.defaultMuted=true;video.loop=true;video.playsInline=true;video.preload='none';
      video.setAttribute('muted','');video.setAttribute('playsinline','');video.setAttribute('aria-hidden','true');
      video.style.cssText='display:block;width:100%;height:100%;margin:0;object-fit:'+(image.getAttribute('preserveAspectRatio')?.includes('slice')?'cover':'contain')+';pointer-events:none';
      foreign.append(video);image.after(foreign);
      const item={video,foreign,visible:false,loading:false,failed:false};videos.push(item);
      video.addEventListener('error',()=>{item.failed=true;foreign.style.visibility='hidden';video.pause();});
      item.update=()=>{
        const play=!disposed&&!doc.hidden&&!reduced.matches&&item.visible&&!item.failed;
        foreign.style.visibility=play?'visible':'hidden';
        if(!play){video.pause();return}
        if(video.src){video.play().catch(()=>{foreign.style.visibility='hidden'});return}
        if(item.loading)return;item.loading=true;
        blob(ref).then(url=>{if(!alive)return;video.src=url;item.update()}).catch(()=>{item.failed=true;foreign.style.visibility='hidden'});
      };
    }
    let alive=true;
    const update=()=>videos.forEach(v=>v.update());
    const observer=new win.IntersectionObserver(rows=>{for(const row of rows){const item=videos.find(v=>v.video===row.target);if(item){item.visible=row.isIntersecting;item.update()}}});
    videos.forEach(v=>observer.observe(v.video));
    doc.addEventListener('visibilitychange',update);reduced.addEventListener('change',update);
    const stop=()=>{if(!alive)return;alive=false;observer.disconnect();doc.removeEventListener('visibilitychange',update);reduced.removeEventListener('change',update);videos.forEach(v=>{v.video.pause();v.video.removeAttribute('src');v.video.load()});host.replaceChildren();cleanups.delete(stop)};
    cleanups.add(stop);return stop;
  }
  function scene(entries) {
    const mounted=new Map();let timer,closed=false;
    const rules=doc.createElement('style');doc.head.append(rules);
    function sync(){
      if(closed)return;
      const desired=new Map();
      for(const entry of entries)for(const el of doc.querySelectorAll(entry.selector))desired.set(el,entry);
      for(const [el,item] of mounted)if(desired.get(el)?.id!==item.entry.id||!el.isConnected||!item.host.isConnected){item.stop();item.host.remove();el.removeAttribute('data-diy-live');mounted.delete(el)}
      for(const [el,entry] of desired){
        if(mounted.has(el))continue;
        const s=win.getComputedStyle(el,'::'+entry.pseudo);
        if(s.display==='none'||s.content==='none'||s.visibility==='hidden')continue;
        const host=doc.createElement('div');host.setAttribute('data-diy-live-slot',entry.id);host.setAttribute('aria-hidden','true');
        for(const key of ['position','top','right','bottom','left','width','height','max-width','min-width','min-height','max-height','aspect-ratio','margin-top','margin-right','margin-bottom','margin-left','align-self','flex','grid-column','transform','transform-origin','z-index','filter','opacity'])host.style.setProperty(key,s.getPropertyValue(key),'important');
        host.style.setProperty('box-sizing','border-box','important');host.style.setProperty('pointer-events','none','important');host.style.setProperty('display','block','important');
        if(s.position==='relative'||s.position==='static'){
          host.style.setProperty('width',entry.id==='main-sidebar'?'calc(100% - 6px)':entry.id==='settings-sidebar'?'calc(100% - '+((parseFloat(s.marginLeft)||0)+(parseFloat(s.marginRight)||0))+'px)':'100%','important');
          if(entry.id!=='main-sidebar')host.style.setProperty('height','auto','important');
        }else if(entry.id==='home'){
          host.style.setProperty('width','auto','important');host.style.setProperty('height','auto','important');
        }
        if(entry.pseudo==='before')el.prepend(host);else el.append(host);
        let stop;
        try{stop=mount(host,entry.svg)}catch(error){host.remove();console.warn('[DIY video]',error.message);continue}
        el.setAttribute('data-diy-live',entry.id);mounted.set(el,{entry,host,stop});
      }
      rules.textContent=entries.map(e=>'[data-diy-live="'+e.id+'"]::'+e.pseudo+'{display:none!important;content:none!important}').join('\n');
      rules.textContent+='[data-diy-live-slot=home]::after{content:"";position:absolute;inset:0;pointer-events:none;background:var(--sj-photo-veil)}';
    }
    const schedule=()=>{win.clearTimeout(timer);timer=win.setTimeout(sync,60)};
    const observer=new win.MutationObserver(rows=>{if(rows.some(r=>!r.target.closest?.('[data-diy-live-slot]')&&([...r.addedNodes].some(n=>n.nodeType===1&&!n.hasAttribute?.('data-diy-live-slot'))||[...r.removedNodes].some(n=>n.nodeType===1))||r.type==='attributes'))schedule()});
    observer.observe(doc.body,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-current','class']});
    const resize=()=>{for(const [el,item] of mounted){item.stop();item.host.remove();el.removeAttribute('data-diy-live')}mounted.clear();rules.textContent='';schedule()};
    win.addEventListener('resize',resize);sync();
    return ()=>{closed=true;observer.disconnect();win.clearTimeout(timer);win.removeEventListener('resize',resize);for(const [el,item] of mounted){item.stop();item.host.remove();el.removeAttribute('data-diy-live')}rules.remove()};
  }
  return {mount,scene,dispose(){disposed=true;for(const stop of [...cleanups])stop();for(const item of media.values()){item.controller.abort();if(item.url)win.URL.revokeObjectURL(item.url)}media.clear()}};
}

function watchJournalVideos(win=window) {
  const doc=win.document,base='/api/skin-center/v2/skins/diy-journal/assets/';
  let stop=null,pending=null,generation=0,closed=false;
  async function sync(){
    const active=doc.documentElement.getAttribute('data-dsh-skin')==='diy-journal';
    if(!active){generation++;pending?.abort();pending=null;stop?.();stop=null;return}
    if(stop||pending||closed)return;
    const epoch=++generation;pending=new win.AbortController();const signal=pending.signal;
    try{
      const response=await win.fetch(base+'diy-generated/videos.json',{signal,credentials:'same-origin'});
      if(!response.ok)return;
      const entries=await response.json();
      if(!Array.isArray(entries)||entries.length>14)throw Error('Invalid media manifest');
      for(const e of entries){
        if(!/^[a-z-]+$/.test(e.id)||!['before','after'].includes(e.pseudo)||!/^diy-generated\/[a-z-]+\.svg$/.test(e.src)||typeof e.selector!=='string')throw Error('Invalid media region');
        const r=await win.fetch(base+e.src,{signal,credentials:'same-origin'});if(!r.ok)throw Error('Missing photo layout');e.svg=await r.text();
      }
      if(epoch!==generation||closed)return;
      const renderer=createJournalVideoRenderer(win,base),unmount=renderer.scene(entries);stop=()=>{unmount();renderer.dispose()};
    }catch(error){if(error.name!=='AbortError')console.warn('[DIY video]',error.message)}finally{if(epoch===generation)pending=null}
  }
  const observer=new win.MutationObserver(sync);observer.observe(doc.documentElement,{attributes:true,attributeFilter:['data-dsh-skin']});sync();
  return ()=>{closed=true;generation++;observer.disconnect();pending?.abort();stop?.()};
}
