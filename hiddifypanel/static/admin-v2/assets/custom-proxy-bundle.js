import{d as B,u as P,y as D,o as t,p as o,w as c,b as s,A as k,C as x,f,e as y,c as p,F as _,D as S,l as h,a as b,E as L,b4 as R,_ as N,aR as O,h as T,z as U,aS as j,B as W,i as F,g as $,G as J}from"./index.js";import{s as A}from"./index2.js";import{s as E}from"./index7.js";import{s as I}from"./SysBadge.js";import{s as C,L as K}from"./LineNumberedCode.js";import{g as z}from"./index5.js";const G={class:"font-semibold mb-2"},H={class:"validation-issue-list mb-0"},q={class:"validation-issue-message"},Q={key:1,class:"validation-issue-detail"},X={class:"validation-issue-list"},Y={class:"validation-issue-message"},Z={class:"validation-preview-pre"},ee=B({__name:"ValidationPanel",props:{result:{}},setup(e,{expose:r}){const n=e,{t:i}=P(),l=L(null);function d(){const a=l.value;return a?a instanceof HTMLElement?a:a.$el??null:null}async function u(){var a;await R(),(a=d())==null||a.scrollIntoView({behavior:"smooth",block:"start"})}return D(()=>n.result,a=>{a&&!a.ok&&u()}),r({scrollIntoView:u}),(a,m)=>e.result?(t(),o(s(A),{key:0,ref_key:"rootEl",ref:l,header:s(i)("validation.title"),class:"validation-panel mb-3"},{default:c(()=>{var v;return[e.result.ok?(t(),o(s(k),{key:0,severity:"success",closable:!1},{default:c(()=>[x(f(s(i)("common.validationOk")),1)]),_:1})):(t(),o(s(k),{key:1,severity:"error",closable:!1,class:"mb-0"},{default:c(()=>[y("div",G,f(s(i)("common.validationFailed")),1),y("ul",H,[(t(!0),p(_,null,S(e.result.errors,(g,w)=>{var V;return t(),p("li",{key:"e"+w,class:"validation-issue"},[g.code?(t(),o(s(I),{key:0,severity:"danger",value:g.code,class:"text-xs mr-2"},null,8,["value"])):h("",!0),y("span",q,f(g.message),1),(V=g.detail)!=null&&V.excerpt?(t(),p("pre",Q,f(g.detail.excerpt),1)):h("",!0)])}),128))])]),_:1})),(v=e.result.warnings)!=null&&v.length?(t(),o(s(E),{key:2,legend:s(i)("validation.warnings"),class:"mt-3 mb-0"},{default:c(()=>[y("ul",X,[(t(!0),p(_,null,S(e.result.warnings,(g,w)=>(t(),p("li",{key:"w"+w,class:"validation-issue"},[g.code?(t(),o(s(I),{key:0,severity:"warn",value:g.code,class:"text-xs mr-2"},null,8,["value"])):h("",!0),y("span",Y,f(g.message),1)]))),128))])]),_:1},8,["legend"])):h("",!0),e.result.compiled_preview?(t(),o(s(E),{key:3,legend:s(i)("validation.preview"),class:"mt-3 mb-0"},{default:c(()=>[b(s(C),{class:"config-scroll-panel",style:{width:"100%",height:"240px"}},{default:c(()=>[y("pre",Z,f(e.result.compiled_preview),1)]),_:1})]),_:1},8,["legend"])):h("",!0)]}),_:1},8,["header"])):h("",!0)}}),be=N(ee,[["__scopeId","data-v-2119ba45"]]);function xe(e,r=5){const n=[...(e==null?void 0:e.errors)??[],...(e==null?void 0:e.warnings)??[]];if(!n.length)return"";const i=n.slice(0,r).map(se);return n.length>r&&i.push(`… +${n.length-r} more`),i.join(" · ")}function se(e){const r=(e.message||"").trim();return e.code&&r&&!r.startsWith(e.code)?`${e.code}: ${r}`:r||e.code||"Unknown validation error"}const te={class:"flex items-start gap-2"},ne={for:"exclude-builtin",class:"cursor-pointer text-sm"},we=B({__name:"BundleExportDialog",props:{visible:{type:Boolean,default:!1},visibleModifiers:{}},emits:j(["confirm"],["update:visible"]),setup(e,{emit:r}){const n=O(e,"visible"),i=r,{t:l}=P(),d=L(!0);D(n,a=>{a&&(d.value=!0)});function u(){i("confirm",d.value),n.value=!1}return(a,m)=>(t(),o(s(U),{visible:n.value,"onUpdate:visible":m[2]||(m[2]=v=>n.value=v),modal:"",header:s(l)("editor.exportBundle"),style:{width:"min(28rem, 96vw)"}},{footer:c(()=>[b(s(T),{label:s(l)("common.cancel"),text:"",onClick:m[1]||(m[1]=v=>n.value=!1)},null,8,["label"]),b(s(T),{label:s(l)("proxy.export"),icon:"pi pi-download",onClick:u},null,8,["label"])]),default:c(()=>[y("div",te,[b(s(z),{modelValue:d.value,"onUpdate:modelValue":m[0]||(m[0]=v=>d.value=v),"input-id":"exclude-builtin",binary:""},null,8,["modelValue"]),y("label",ne,f(s(l)("editor.excludeBuiltinTemplates")),1)])]),_:1},8,["visible","header"]))}});var re=`
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
`,ie={root:"p-progressspinner",spin:"p-progressspinner-spin",circle:"p-progressspinner-circle"},ae=W.extend({name:"progressspinner",style:re,classes:ie}),le={name:"BaseProgressSpinner",extends:F,props:{strokeWidth:{type:String,default:"2"},fill:{type:String,default:"none"},animationDuration:{type:String,default:"2s"}},style:ae,provide:function(){return{$pcProgressSpinner:this,$parentInstance:this}}},M={name:"ProgressSpinner",extends:le,inheritAttrs:!1,computed:{svgStyle:function(){return{"animation-duration":this.animationDuration}}}},oe=["fill","stroke-width"];function ce(e,r,n,i,l,d){return t(),p("div",$({class:e.cx("root"),role:"progressbar"},e.ptmi("root")),[(t(),p("svg",$({class:e.cx("spin"),viewBox:"25 25 50 50",style:d.svgStyle},e.ptm("spin")),[y("circle",$({class:e.cx("circle"),cx:"50",cy:"50",r:"20",fill:e.fill,"stroke-width":e.strokeWidth,strokeMiterlimit:"10"},e.ptm("circle")),null,16,oe)],16))],16)}M.render=ce;const de={key:0,class:"flex justify-center py-8"},ue={key:1,class:"flex flex-col gap-3"},pe={key:4,class:"m-0 pl-4 text-sm"},fe=B({__name:"TemplatePreviewDialog",props:j({loading:{type:Boolean},result:{}},{visible:{type:Boolean,default:!1},visibleModifiers:{}}),emits:["update:visible"],setup(e){const r=e,n=O(e,"visible"),{t:i}=P(),l=J(()=>{if(!r.result)return"";if(r.result.skipped)return"SKIP";const d=r.result.rendered??"",u=d.trim();if(!u.startsWith("{")&&!u.startsWith("["))return d;try{return JSON.stringify(JSON.parse(u),null,2)}catch{return d}});return(d,u)=>(t(),o(s(U),{visible:n.value,"onUpdate:visible":u[0]||(u[0]=a=>n.value=a),modal:"",class:"w-full max-w-3xl",header:s(i)("editor.previewTitle")},{default:c(()=>{var a;return[e.loading?(t(),p("div",de,[b(s(M),{style:{width:"2.5rem",height:"2.5rem"}})])):e.result?(t(),p("div",ue,[e.result.skipped?(t(),o(s(k),{key:0,severity:"info",closable:!1},{default:c(()=>[...u[1]||(u[1]=[x(" SKIP ",-1)])]),_:1})):e.result.error?(t(),o(s(k),{key:1,severity:"error",closable:!1},{default:c(()=>[x(f(e.result.error),1)]),_:1})):e.result.ok?(t(),o(s(k),{key:2,severity:"success",closable:!1},{default:c(()=>[x(f(s(i)("editor.previewOk")),1)]),_:1})):(t(),o(s(k),{key:3,severity:"warn",closable:!1},{default:c(()=>[x(f(s(i)("editor.previewPartial")),1)]),_:1})),(a=e.result.warnings)!=null&&a.length?(t(),p("ul",pe,[(t(!0),p(_,null,S(e.result.warnings,(m,v)=>(t(),p("li",{key:v},f(m.message),1))),128))])):h("",!0),l.value?(t(),o(s(C),{key:5,class:"preview-scroll-panel",style:{width:"100%",height:"420px"}},{default:c(()=>[b(K,{text:l.value},null,8,["text"])]),_:1})):h("",!0)])):h("",!0)]}),_:1},8,["visible","header"]))}}),$e=N(fe,[["__scopeId","data-v-b51e3a88"]]);function _e(e,r){const n=new Blob([JSON.stringify(e,null,2)],{type:"application/json"}),i=URL.createObjectURL(n),l=document.createElement("a");l.href=i,l.download=r,l.click(),URL.revokeObjectURL(i)}function Se(e=".json,application/json"){return new Promise(r=>{const n=document.createElement("input");n.type="file",n.accept=e,n.onchange=()=>{var i;return r(((i=n.files)==null?void 0:i[0])??null)},n.click()})}export{$e as T,be as V,we as _,_e as d,Se as p,xe as v};
