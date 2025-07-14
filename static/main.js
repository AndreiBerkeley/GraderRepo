// ---------- element refs ----------
const els = {
  contest:  document.getElementById('contest'),
  year:     document.getElementById('year'),
  problem:  document.getElementById('problem'),
  candidate:document.getElementById('candidate'),
  candWrap: document.getElementById('cand-wrap'),
  official: document.getElementById('official'),
  draft:    document.getElementById('draft'),
  form:     document.getElementById('review-form'),
  status:   document.getElementById('status')
};

// ---------- globals ----------
let contestIndex = {};   // official problems {contest:[years]}
let candidates    = [];  // ["alice", "bert", …]
let rows          = [];  // current contest/year rows
let annotations   = [];

// ---------- load indices ----------
Promise.all([
  fetch('data/index.json').then(r=>r.json()),
  fetch('outputs/index.json').then(r=>r.json()).catch(()=>[])   // outputs optional
]).then(([idx,cands])=>{
  contestIndex = idx;
  candidates   = cands;
  populate(els.contest,Object.keys(idx));
  populate(els.candidate,cands);
  els.contest.dispatchEvent(new Event('change'));
});

function populate(sel,items){ sel.innerHTML = items.map(x=>`<option>${x}</option>`).join(''); }

// ---------- cascading dropdowns ----------
els.contest.addEventListener('change',()=>{
  populate(els.year, contestIndex[els.contest.value] || []);
  els.year.dispatchEvent(new Event('change'));
});

els.year.addEventListener('change',()=>{
  const p=`data/${els.contest.value}/${els.year.value}.jsonl`;
  fetch(p).then(r=>r.text()).then(t=>{
    rows = t.trim().split(/\n+/).map(JSON.parse);
    populate(els.problem, rows.map(o=>o.id||o.problem||o.number));
    els.problem.dispatchEvent(new Event('change'));
  });
});

// ---------- problem or candidate change ----------
['problem','candidate'].forEach(id=>els[id].addEventListener('change',render));

function render(){
  const id = els.problem.value;
  const row= rows.find(o=>(o.id||o.problem)==id);
  if(!row) return;

  // official
  els.official.innerHTML = `<div class="tex-block">${cleanupTex(row.question)}\n<hr>\n${cleanupTex(row.solution)}</div>`;

  // draft
  const cand = els.candidate.value;
  if(!cand){ els.candWrap.hidden=true; els.draft.innerHTML='<em>No draft selected.</em>'; return; }
  els.candWrap.hidden=false;
  const path = `outputs/${cand}/${els.contest.value}-${els.year.value}-sol${id.replace(/.*?(\d+)$/,'$1')}.tex`;
  fetch(path).then(r=> r.ok ? r.text() : null).then(tex=>{
     els.draft.innerHTML = tex ? `<div class="tex-block">${cleanupTex(tex)}</div>` : '<em>No draft available.</em>';
     annotations=[];
     MathJax.typesetPromise();
  });
}
function cleanupTex(src){
  return src
    .replace(/\\textsl\{[^}]*Available online[^}]*}/g,'')               // drop AoPS line
    .replace(/\\url\{([^}]+)}/g,'<a href="$1" target="_blank">$1</a>')// make links clickable
    .replace(/\\(?:big|med|small)skip/g,'<br><br>')                       // spacing
    .replace(/\\begin\{(?:mdframed|asy)[\s\S]*?\\end\{(?:mdframed|asy)}/g,'')
    .replace(/\\pagebreak/g,'');
}

// ---------- annotation: highlight + comment ----------
els.draft.addEventListener('mouseup',()=>{
  const sel=window.getSelection();
  if(!sel || sel.isCollapsed || !els.draft.contains(sel.anchorNode)) return;
  const text=sel.toString();
  const comment=prompt('Comment on highlighted text:','');
  if(!comment){sel.removeAllRanges(); return;}

  const range=sel.getRangeAt(0).cloneRange();
  const span=document.createElement('span');
  span.className='mark'; span.textContent=text; span.dataset.comment=comment;
  range.deleteContents(); range.insertNode(span);
  annotations.push({text,comment});
  sel.removeAllRanges();
});

// hover tooltip
els.draft.addEventListener('mouseover',e=>{
  if(!e.target.classList.contains('mark')) return;
  const pop=document.createElement('div'); pop.className='comment-pop'; pop.textContent=e.target.dataset.comment;
  document.body.appendChild(pop);
  const r=e.target.getBoundingClientRect();
  pop.style.left=`${r.left+r.width/2}px`; pop.style.top=`${r.top-4}px`;
  e.target.addEventListener('mouseleave',()=>pop.remove(),{once:true});
});

// ---------- submit review + annotations ----------
els.form.addEventListener('submit',ev=>{
  ev.preventDefault();
  const payload={
    contest: els.contest.value,
    year:    els.year.value,
    problem: els.problem.value,
    data:{
      correctness:+ev.target.correctness.value,
      relevance:  +ev.target.relevance.value,
      remarks:    ev.target.remarks.value.trim()
    },
    annotations // for convenience we send to /save too (harmless)
  };

  const headers={'Content-Type':'application/json'};
  Promise.all([
    fetch('/save',     {method:'POST',headers,body:JSON.stringify(payload)}),
    fetch('/annotate', {method:'POST',headers,body:JSON.stringify({
      contest:payload.contest,year:payload.year,problem:payload.problem,annotations})})
  ])
  .then(r=>r.every(res=>res.ok)?show('✓ Saved'):Promise.reject())
  .catch(()=>show('✗ Failed',true));
});

function show(msg,err=false){
  els.status.hidden=false; els.status.textContent=msg;
  els.status.style.color=err?'crimson':'green';
  setTimeout(()=>els.status.hidden=true,3000);
}
