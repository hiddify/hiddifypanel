import{d as B,u as P,o as s,p as u,w as l,b as t,A as y,C as k,f,e as h,c,F as $,D as S,l as g,a as b,_ as N,aR as O,y as T,h as V,z as _,aS as C,E as U,B as j,i as I,g as w,G as E}from"./index.js";import{s as M}from"./index2.js";import{s as x}from"./index7.js";import{s as D,L as R}from"./LineNumberedCode.js";import{g as F}from"./index5.js";const J={class:"validation-preview-pre"},W=B({__name:"ValidationPanel",props:{result:{}},setup(e){const{t:r}=P();return(n,d)=>e.result?(s(),u(t(M),{key:0,header:t(r)("validation.title")},{default:l(()=>{var i,a;return[e.result.ok?(s(),u(t(y),{key:0,severity:"success"},{default:l(()=>[k(f(t(r)("common.validationOk")),1)]),_:1})):(s(),u(t(y),{key:1,severity:"error"},{default:l(()=>[k(f(t(r)("common.validationFailed")),1)]),_:1})),(i=e.result.errors)!=null&&i.length?(s(),u(t(x),{key:2,legend:t(r)("validation.errors")},{default:l(()=>[h("ul",null,[(s(!0),c($,null,S(e.result.errors,(o,p)=>(s(),c("li",{key:"e"+p},f(o.message),1))),128))])]),_:1},8,["legend"])):g("",!0),(a=e.result.warnings)!=null&&a.length?(s(),u(t(x),{key:3,legend:t(r)("validation.warnings")},{default:l(()=>[h("ul",null,[(s(!0),c($,null,S(e.result.warnings,(o,p)=>(s(),c("li",{key:"w"+p},f(o.message),1))),128))])]),_:1},8,["legend"])):g("",!0),e.result.compiled_preview?(s(),u(t(x),{key:4,legend:t(r)("validation.preview")},{default:l(()=>[b(t(D),{class:"config-scroll-panel",style:{width:"100%",height:"240px"}},{default:l(()=>[h("pre",J,f(e.result.compiled_preview),1)]),_:1})]),_:1},8,["legend"])):g("",!0)]}),_:1},8,["header"])):g("",!0)}}),ae=N(W,[["__scopeId","data-v-0585d984"]]),A={class:"flex items-start gap-2"},K={for:"exclude-builtin",class:"cursor-pointer text-sm"},oe=B({__name:"BundleExportDialog",props:{visible:{type:Boolean,default:!1},visibleModifiers:{}},emits:C(["confirm"],["update:visible"]),setup(e,{emit:r}){const n=O(e,"visible"),d=r,{t:i}=P(),a=U(!0);T(n,p=>{p&&(a.value=!0)});function o(){d("confirm",a.value),n.value=!1}return(p,m)=>(s(),u(t(_),{visible:n.value,"onUpdate:visible":m[2]||(m[2]=v=>n.value=v),modal:"",header:t(i)("editor.exportBundle"),style:{width:"min(28rem, 96vw)"}},{footer:l(()=>[b(t(V),{label:t(i)("common.cancel"),text:"",onClick:m[1]||(m[1]=v=>n.value=!1)},null,8,["label"]),b(t(V),{label:t(i)("proxy.export"),icon:"pi pi-download",onClick:o},null,8,["label"])]),default:l(()=>[h("div",A,[b(t(F),{modelValue:a.value,"onUpdate:modelValue":m[0]||(m[0]=v=>a.value=v),"input-id":"exclude-builtin",binary:""},null,8,["modelValue"]),h("label",K,f(t(i)("editor.excludeBuiltinTemplates")),1)])]),_:1},8,["visible","header"]))}});var z=`
    .p-progressspinner {
        position: relative;
        margin: 0 auto;
        width: 100px;
        height: 100px;
        display: inline-block;
    }

    .p-progressspinner::before {
        content: '';
        display: block;
        padding-top: 100%;
    }

    .p-progressspinner-spin {
        height: 100%;
        transform-origin: center center;
        width: 100%;
        position: absolute;
        top: 0;
        bottom: 0;
        left: 0;
        right: 0;
        margin: auto;
        animation: p-progressspinner-rotate 2s linear infinite;
    }

    .p-progressspinner-circle {
        stroke-dasharray: 89, 200;
        stroke-dashoffset: 0;
        stroke: dt('progressspinner.colorOne');
        animation:
            p-progressspinner-dash 1.5s ease-in-out infinite,
            p-progressspinner-color 6s ease-in-out infinite;
        stroke-linecap: round;
    }

    @keyframes p-progressspinner-rotate {
        100% {
            transform: rotate(360deg);
        }
    }
    @keyframes p-progressspinner-dash {
        0% {
            stroke-dasharray: 1, 200;
            stroke-dashoffset: 0;
        }
        50% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -35px;
        }
        100% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -124px;
        }
    }
    @keyframes p-progressspinner-color {
        100%,
        0% {
            stroke: dt('progressspinner.color.one');
        }
        40% {
            stroke: dt('progressspinner.color.two');
        }
        66% {
            stroke: dt('progressspinner.color.three');
        }
        80%,
        90% {
            stroke: dt('progressspinner.color.four');
        }
    }
`,G={root:"p-progressspinner",spin:"p-progressspinner-spin",circle:"p-progressspinner-circle"},q=j.extend({name:"progressspinner",style:z,classes:G}),H={name:"BaseProgressSpinner",extends:I,props:{strokeWidth:{type:String,default:"2"},fill:{type:String,default:"none"},animationDuration:{type:String,default:"2s"}},style:q,provide:function(){return{$pcProgressSpinner:this,$parentInstance:this}}},L={name:"ProgressSpinner",extends:H,inheritAttrs:!1,computed:{svgStyle:function(){return{"animation-duration":this.animationDuration}}}},Q=["fill","stroke-width"];function X(e,r,n,d,i,a){return s(),c("div",w({class:e.cx("root"),role:"progressbar"},e.ptmi("root")),[(s(),c("svg",w({class:e.cx("spin"),viewBox:"25 25 50 50",style:a.svgStyle},e.ptm("spin")),[h("circle",w({class:e.cx("circle"),cx:"50",cy:"50",r:"20",fill:e.fill,"stroke-width":e.strokeWidth,strokeMiterlimit:"10"},e.ptm("circle")),null,16,Q)],16))],16)}L.render=X;const Y={key:0,class:"flex justify-center py-8"},Z={key:1,class:"flex flex-col gap-3"},ee={key:4,class:"m-0 pl-4 text-sm"},te=B({__name:"TemplatePreviewDialog",props:C({loading:{type:Boolean},result:{}},{visible:{type:Boolean,default:!1},visibleModifiers:{}}),emits:["update:visible"],setup(e){const r=e,n=O(e,"visible"),{t:d}=P(),i=E(()=>{if(!r.result)return"";if(r.result.skipped)return"SKIP";const a=r.result.rendered??"",o=a.trim();if(!o.startsWith("{")&&!o.startsWith("["))return a;try{return JSON.stringify(JSON.parse(o),null,2)}catch{return a}});return(a,o)=>(s(),u(t(_),{visible:n.value,"onUpdate:visible":o[0]||(o[0]=p=>n.value=p),modal:"",class:"w-full max-w-3xl",header:t(d)("editor.previewTitle")},{default:l(()=>{var p;return[e.loading?(s(),c("div",Y,[b(t(L),{style:{width:"2.5rem",height:"2.5rem"}})])):e.result?(s(),c("div",Z,[e.result.skipped?(s(),u(t(y),{key:0,severity:"info",closable:!1},{default:l(()=>[...o[1]||(o[1]=[k(" SKIP ",-1)])]),_:1})):e.result.error?(s(),u(t(y),{key:1,severity:"error",closable:!1},{default:l(()=>[k(f(e.result.error),1)]),_:1})):e.result.ok?(s(),u(t(y),{key:2,severity:"success",closable:!1},{default:l(()=>[k(f(t(d)("editor.previewOk")),1)]),_:1})):(s(),u(t(y),{key:3,severity:"warn",closable:!1},{default:l(()=>[k(f(t(d)("editor.previewPartial")),1)]),_:1})),(p=e.result.warnings)!=null&&p.length?(s(),c("ul",ee,[(s(!0),c($,null,S(e.result.warnings,(m,v)=>(s(),c("li",{key:v},f(m.message),1))),128))])):g("",!0),i.value?(s(),u(t(D),{key:5,class:"preview-scroll-panel",style:{width:"100%",height:"420px"}},{default:l(()=>[b(R,{text:i.value},null,8,["text"])]),_:1})):g("",!0)])):g("",!0)]}),_:1},8,["visible","header"]))}}),de=N(te,[["__scopeId","data-v-b51e3a88"]]);function ue(e,r){const n=new Blob([JSON.stringify(e,null,2)],{type:"application/json"}),d=URL.createObjectURL(n),i=document.createElement("a");i.href=d,i.download=r,i.click(),URL.revokeObjectURL(d)}function pe(e=".json,application/json"){return new Promise(r=>{const n=document.createElement("input");n.type="file",n.accept=e,n.onchange=()=>{var d;return r(((d=n.files)==null?void 0:d[0])??null)},n.click()})}export{de as T,ae as V,oe as _,ue as d,pe as p};
