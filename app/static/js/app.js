const $=s=>document.querySelector(s);
async function api(path,options={}){const r=await fetch('/api'+path,{...options,headers:{...(options.headers||{}),...(window.ikaCsrf?{'X-CSRF-Token':window.ikaCsrf}:{})}});const data=r.status===204?{}:await r.json();if(!r.ok)throw Error(data.error?.message||'Request failed');return data}
function node(tag,text='',cls=''){const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e}
function show(tab){document.querySelectorAll('main section').forEach(s=>s.hidden=s.id!==tab);if(tab==='dashboard')loadStats();if(tab==='documents')loadDocs();if(tab==='system')loadHealth()}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.tab)));
async function loadStats(){try{const d=await api('/dashboard/stats');const box=$('#stats');box.replaceChildren();for(const [k,v] of Object.entries({...d,...d.statuses})){if(typeof v==='number'){const card=node('div','','card');card.append(node('strong',String(v)),node('span',k.replaceAll('_',' ')));box.append(card)}}}catch(e){$('#stats').textContent=e.message}}
let docsRequest=0;
async function loadDocs(){
 const token=++docsRequest,box=$('#document-list');
 try{
  const d=await api('/documents');
  if(token!==docsRequest)return;
  box.replaceChildren();
  for(const doc of d.documents){
   const row=node('div','','entry');
   row.append(node('strong',doc.filename));
   const meta=node('div','','doc-meta');
   meta.append(node('span',doc.status,'doc-status '+doc.status),node('span',`${doc.pages} pages · ${doc.chunks} chunks`));
   row.append(meta);
   if(doc.status==='pending'||doc.status==='processing'){
    try{
     const jobs=await api('/documents/'+encodeURIComponent(doc.id)+'/jobs'),job=jobs.jobs[0];
     if(job){
      row.append(node('p',`Indexing job: ${job.status} (${job.progress}%)`));
      const progress=document.createElement('progress');progress.max=100;progress.value=job.progress;progress.className='job-progress';row.append(progress);
     }
    }catch(_){row.append(node('p','Indexing status temporarily unavailable'))}
   }
   if(doc.error)row.append(node('p',doc.error,'error-note'));
   const actions=node('div','','doc-actions');
   const del=node('button','Delete');del.disabled=['pending','processing'].includes(doc.status);
   del.onclick=async()=>{if(confirm('Delete this document?')){try{await api('/documents/'+encodeURIComponent(doc.id),{method:'DELETE'});loadDocs()}catch(e){alert(e.message)}}};
   const re=node('button','Reindex');re.disabled=['pending','processing'].includes(doc.status);
   re.onclick=async()=>{try{await api('/documents/'+encodeURIComponent(doc.id)+'/reindex',{method:'POST'});loadDocs()}catch(e){alert(e.message)}};
   actions.append(del,re);row.append(actions);box.append(row);
  }
 }catch(e){if(token===docsRequest)box.textContent=e.message}
}
$('#upload-form').onsubmit=e=>{e.preventDefault();const f=$('#file').files[0];if(!f)return;const fd=new FormData();fd.append('file',f);const status=$('#upload-status'),progress=$('#upload-progress');progress.hidden=false;progress.value=0;status.textContent='Uploading PDF…';const xhr=new XMLHttpRequest();xhr.open('POST','/api/documents');if(window.ikaCsrf)xhr.setRequestHeader('X-CSRF-Token',window.ikaCsrf);xhr.upload.onprogress=event=>{if(event.lengthComputable){progress.value=Math.round(event.loaded*100/event.total);status.textContent=`Uploading PDF: ${progress.value}%`}};xhr.onload=()=>{progress.hidden=true;let data={};try{data=JSON.parse(xhr.responseText)}catch(_){}if(xhr.status>=200&&xhr.status<300){status.textContent='Upload complete. Indexing queued: '+data.job_id;$('#file').value='';loadDocs()}else status.textContent=data.error?.message||`Upload failed (${xhr.status})`};xhr.onerror=()=>{progress.hidden=true;status.textContent='Network error during upload'};xhr.send(fd)};
let conversation=null;
async function loadConversations(){
 const list=$('#conversation-list'),term=$('#conversation-search').value.trim();
 try{
  const d=await api('/conversations'+(term?'?search='+encodeURIComponent(term):''));
  list.replaceChildren();
  if(!d.conversations.length)list.append(node('p','No conversations found.'));
  for(const c of d.conversations){
   const row=node('div','','conversation-row');
   const open=node('button',c.title);open.type='button';open.onclick=()=>openConversation(c.id);
   const rename=node('button','Rename');rename.type='button';rename.onclick=async()=>{
    const title=prompt('Conversation title:',c.title);if(title===null)return;
    if(!title.trim()||title.trim().length>180){$('#conversation-notice').textContent='Title must contain 1–180 characters.';return}
    try{await api('/conversations/'+encodeURIComponent(c.id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:title.trim()})});await loadConversations()}catch(e){$('#conversation-notice').textContent=e.message}
   };
   const del=node('button','Delete');del.type='button';del.onclick=async()=>{
    if(!confirm('Permanently delete this conversation and its messages?'))return;
    try{await api('/conversations/'+encodeURIComponent(c.id),{method:'DELETE'});if(conversation===c.id){conversation=null;$('#messages').replaceChildren();$('#retrieval-results').replaceChildren()};await loadConversations()}catch(e){$('#conversation-notice').textContent=e.message}
   };
   row.append(open,rename,del);list.append(row)
  }
 }catch(e){$('#conversation-notice').textContent=e.message}
}
async function openConversation(id){
 try{
  const c=await api('/conversations/'+encodeURIComponent(id));conversation=c.id;
  const box=$('#messages');box.replaceChildren();$('#retrieval-results').replaceChildren();
  for(const m of c.messages){box.append(node('div',(m.role==='user'?'You: ':'IKA: ')+m.content,'entry'));
   for(const s of m.sources||[]){const d=document.createElement('details');d.append(node('summary',`Source: page ${s.page}`),node('p',s.excerpt));box.append(d)}
  }
  $('#conversation-notice').textContent='Opened: '+c.title;
  box.scrollTop=box.scrollHeight
 }catch(e){$('#conversation-notice').textContent=e.message}
}
$('#new-conversation').onclick=()=>{conversation=null;$('#messages').replaceChildren();$('#retrieval-results').replaceChildren();$('#conversation-notice').textContent='New conversation ready.'};
$('#refresh-conversations').onclick=loadConversations;
$('#conversation-search').addEventListener('input',()=>loadConversations());

$('#chat-form').onsubmit=async e=>{
 e.preventDefault();
 const question=$('#question').value.trim();
 if(!question)return;
 const box=$('#messages');
 box.append(node('div','You: '+question,'entry'));$('#question').value='';
 const loading=node('div','Generating…');box.append(loading);
 try{
  const r=await api('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,conversation_id:conversation})});
  conversation=r.conversation_id;
  loading.replaceWith(node('div','IKA: '+r.answer,'entry'));
  for(const source of r.sources||[]){
   const detail=document.createElement('details');
   detail.append(node('summary',`[SOURCE ${source.source_number}] ${source.title}, page ${source.page}`),node('p',source.excerpt));
   box.append(detail);
  }
  const inspect=$('#retrieval-results');inspect.replaceChildren();
  const diagnostics=r.retrieval_diagnostics||[];
  if(!diagnostics.length)inspect.append(node('p','No retrieval candidates returned.'));
  for(const [i,result] of diagnostics.entries()){
   const item=node('div','','entry');
   item.append(node('strong',`${i+1}. ${result.title} — page ${result.page}`));
   const methods=(result.retrieval_methods||[]).join(', ')||'unknown';
   const distance=typeof result.distance==='number'?result.distance.toFixed(4):'not available';
   item.append(node('p',`Distance: ${distance} · Hybrid score: ${typeof result.hybrid_score==='number'?result.hybrid_score.toFixed(4):'not available'} · Method: ${methods} · Answer key: ${result.answer_key_detected?'yes':'no'}`));
   const source=(r.sources||[]).find(candidate=>candidate.chunk_id===result.chunk_id);
   if(source){
    const detail=document.createElement('details');
    detail.append(node('summary',`View cited excerpt [SOURCE ${source.source_number}]`),node('p',source.excerpt));
    item.append(detail);
   }
   inspect.append(item);
  }
 }catch(err){loading.textContent=err.message}
 box.scrollTop=box.scrollHeight;loadConversations();
};
async function loadHealth(){try{const [h,m]=await Promise.all([api('/system/health'),api('/models')]);$('#health').textContent=JSON.stringify(h,null,2);$('#models').textContent=JSON.stringify(m,null,2);$('#status').textContent='Ollama: '+h.ollama}catch(e){$('#health').textContent=e.message}}
loadStats();loadHealth();loadConversations();
