function l(t){return t.flatMap(a=>(a.variables??[]).map(e=>({...e,category:e.category??a.id,category_label:a.label})))}export{l as f};
