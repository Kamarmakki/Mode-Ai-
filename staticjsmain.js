document.getElementById('btnAnalyze').onclick = async () => {
  const kw = document.getElementById('keyword').value.trim();
  if(!kw){alert('أدخل كلمة مفتاحية');return;}
  document.getElementById('results').classList.add('d-none');
  const res = await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword:kw})});
  const data = await res.json();
  if(data.error){alert(data.error);return;}
  ['suggested_title','meta_description','snippet_text','nlp_keywords','featured_snippets'].forEach(f=>{
    document.getElementById(f).textContent = data[f] || '';
  });
  const ol = document.getElementById('outline');ol.innerHTML='';
  data.outline.forEach(h=> ol.insertAdjacentHTML('beforeend',`<li>${h.text}</li>`));
  document.getElementById('results').classList.remove('d-none');
};