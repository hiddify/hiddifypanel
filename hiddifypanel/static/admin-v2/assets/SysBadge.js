import{B as z,L as U,M as B,N as c,O as f,P as $,Q as F,W as M,S as V,$ as Z,U as b,V as k,X as N,Y,Z as K,a0 as h,a1 as w,a2 as H,a3 as q,i as P,j as Q,o as p,c as y,p as A,g as v,q as X,l as _,k as T,e as O,f as G,a4 as J,R as tt,a5 as et,a6 as ot,a7 as nt,a8 as it,a9 as rt,aa as R,ab as st,ac as lt,r as at,ad as dt,w as S,a as pt,T as ut,v as I,d as ct,u as ft,b as C,_ as vt}from"./index.js";import{C as j,O as E}from"./index5.js";var ht=`
    .p-tooltip {
        position: absolute;
        display: none;
        max-width: dt('tooltip.max.width');
    }

    .p-tooltip-right,
    .p-tooltip-left {
        padding: 0 dt('tooltip.gutter');
    }

    .p-tooltip-top,
    .p-tooltip-bottom {
        padding: dt('tooltip.gutter') 0;
    }

    .p-tooltip-text {
        white-space: pre-line;
        word-break: break-word;
        background: dt('tooltip.background');
        color: dt('tooltip.color');
        padding: dt('tooltip.padding');
        box-shadow: dt('tooltip.shadow');
        border-radius: dt('tooltip.border.radius');
    }

    .p-tooltip-arrow {
        position: absolute;
        width: 0;
        height: 0;
        border-color: transparent;
        border-style: solid;
    }

    .p-tooltip-right .p-tooltip-arrow {
        margin-top: calc(-1 * dt('tooltip.gutter'));
        border-width: dt('tooltip.gutter') dt('tooltip.gutter') dt('tooltip.gutter') 0;
        border-right-color: dt('tooltip.background');
    }

    .p-tooltip-left .p-tooltip-arrow {
        margin-top: calc(-1 * dt('tooltip.gutter'));
        border-width: dt('tooltip.gutter') 0 dt('tooltip.gutter') dt('tooltip.gutter');
        border-left-color: dt('tooltip.background');
    }

    .p-tooltip-top .p-tooltip-arrow {
        margin-left: calc(-1 * dt('tooltip.gutter'));
        border-width: dt('tooltip.gutter') dt('tooltip.gutter') 0 dt('tooltip.gutter');
        border-top-color: dt('tooltip.background');
        border-bottom-color: dt('tooltip.background');
    }

    .p-tooltip-bottom .p-tooltip-arrow {
        margin-left: calc(-1 * dt('tooltip.gutter'));
        border-width: 0 dt('tooltip.gutter') dt('tooltip.gutter') dt('tooltip.gutter');
        border-top-color: dt('tooltip.background');
        border-bottom-color: dt('tooltip.background');
    }
`,gt={root:"p-tooltip p-component",arrow:"p-tooltip-arrow",text:"p-tooltip-text"},bt=z.extend({name:"tooltip-directive",style:ht,classes:gt}),yt=q.extend({style:bt});function mt(o,t){return Lt(o)||_t(o,t)||Et(o,t)||wt()}function wt(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Et(o,t){if(o){if(typeof o=="string")return D(o,t);var e={}.toString.call(o).slice(8,-1);return e==="Object"&&o.constructor&&(e=o.constructor.name),e==="Map"||e==="Set"?Array.from(o):e==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(e)?D(o,t):void 0}}function D(o,t){(t==null||t>o.length)&&(t=o.length);for(var e=0,n=Array(t);e<t;e++)n[e]=o[e];return n}function _t(o,t){var e=o==null?null:typeof Symbol<"u"&&o[Symbol.iterator]||o["@@iterator"];if(e!=null){var n,i,r,s,d=[],l=!0,a=!1;try{if(r=(e=e.call(o)).next,t!==0)for(;!(l=(n=r.call(e)).done)&&(d.push(n.value),d.length!==t);l=!0);}catch(g){a=!0,i=g}finally{try{if(!l&&e.return!=null&&(s=e.return(),Object(s)!==s))return}finally{if(a)throw i}}return d}}function Lt(o){if(Array.isArray(o))return o}function x(o,t,e){return(t=$t(t))in o?Object.defineProperty(o,t,{value:e,enumerable:!0,configurable:!0,writable:!0}):o[t]=e,o}function $t(o){var t=kt(o,"string");return u(t)=="symbol"?t:t+""}function kt(o,t){if(u(o)!="object"||!o)return o;var e=o[Symbol.toPrimitive];if(e!==void 0){var n=e.call(o,t);if(u(n)!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(o)}function u(o){"@babel/helpers - typeof";return u=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},u(o)}var Ct=yt.extend("tooltip",{beforeMount:function(t,e){var n,i=this.getTarget(t);if(i.$_ptooltipModifiers=this.getModifiers(e),e.value){if(typeof e.value=="string")i.$_ptooltipValue=e.value,i.$_ptooltipDisabled=!1,i.$_ptooltipEscape=!0,i.$_ptooltipClass=null,i.$_ptooltipFitContent=!0,i.$_ptooltipIdAttr=w("pv_id")+"_tooltip",i.$_ptooltipShowDelay=0,i.$_ptooltipHideDelay=0,i.$_ptooltipAutoHide=!0;else if(u(e.value)==="object"&&e.value){if(H(e.value.value)||e.value.value.trim()==="")return;i.$_ptooltipValue=e.value.value,i.$_ptooltipDisabled=!!e.value.disabled===e.value.disabled?e.value.disabled:!1,i.$_ptooltipEscape=!!e.value.escape===e.value.escape?e.value.escape:!0,i.$_ptooltipClass=e.value.class||"",i.$_ptooltipFitContent=!!e.value.fitContent===e.value.fitContent?e.value.fitContent:!0,i.$_ptooltipIdAttr=e.value.id||w("pv_id")+"_tooltip",i.$_ptooltipShowDelay=e.value.showDelay||0,i.$_ptooltipHideDelay=e.value.hideDelay||0,i.$_ptooltipAutoHide=!!e.value.autoHide===e.value.autoHide?e.value.autoHide:!0}}else return;i.$_ptooltipZIndex=(n=e.instance.$primevue)===null||n===void 0||(n=n.config)===null||n===void 0||(n=n.zIndex)===null||n===void 0?void 0:n.tooltip,this.bindEvents(i,e),t.setAttribute("data-pd-tooltip",!0)},updated:function(t,e){var n=this.getTarget(t);if(n.$_ptooltipModifiers=this.getModifiers(e),this.unbindEvents(n),!!e.value){if(typeof e.value=="string")n.$_ptooltipValue=e.value,n.$_ptooltipDisabled=!1,n.$_ptooltipEscape=!0,n.$_ptooltipClass=null,n.$_ptooltipIdAttr=n.$_ptooltipIdAttr||w("pv_id")+"_tooltip",n.$_ptooltipShowDelay=0,n.$_ptooltipHideDelay=0,n.$_ptooltipAutoHide=!0,this.bindEvents(n,e);else if(u(e.value)==="object"&&e.value)if(H(e.value.value)||e.value.value.trim()===""){this.unbindEvents(n,e);return}else n.$_ptooltipValue=e.value.value,n.$_ptooltipDisabled=!!e.value.disabled===e.value.disabled?e.value.disabled:!1,n.$_ptooltipEscape=!!e.value.escape===e.value.escape?e.value.escape:!0,n.$_ptooltipClass=e.value.class||"",n.$_ptooltipFitContent=!!e.value.fitContent===e.value.fitContent?e.value.fitContent:!0,n.$_ptooltipIdAttr=e.value.id||n.$_ptooltipIdAttr||w("pv_id")+"_tooltip",n.$_ptooltipShowDelay=e.value.showDelay||0,n.$_ptooltipHideDelay=e.value.hideDelay||0,n.$_ptooltipAutoHide=!!e.value.autoHide===e.value.autoHide?e.value.autoHide:!0,this.bindEvents(n,e)}},unmounted:function(t,e){var n=this.getTarget(t);this.hide(t,0),this.remove(n),this.unbindEvents(n,e),n.$_ptooltipScrollHandler&&(n.$_ptooltipScrollHandler.destroy(),n.$_ptooltipScrollHandler=null)},methods:{bindEvents:function(t,e){var n=this,i=t.$_ptooltipModifiers;i.focus?(t.$_ptooltipFocusEvent=function(r){return n.onFocus(r,e)},t.$_ptooltipBlurEvent=this.onBlur.bind(this),t.addEventListener("focus",t.$_ptooltipFocusEvent),t.addEventListener("blur",t.$_ptooltipBlurEvent)):(t.$_ptooltipMouseEnterEvent=function(r){return n.onMouseEnter(r,e)},t.$_ptooltipMouseLeaveEvent=this.onMouseLeave.bind(this),t.$_ptooltipClickEvent=this.onClick.bind(this),t.addEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),t.addEventListener("mouseleave",t.$_ptooltipMouseLeaveEvent),t.addEventListener("click",t.$_ptooltipClickEvent)),t.$_ptooltipKeydownEvent=this.onKeydown.bind(this),t.addEventListener("keydown",t.$_ptooltipKeydownEvent),t.$_pWindowResizeEvent=this.onWindowResize.bind(this,t)},unbindEvents:function(t){var e=t.$_ptooltipModifiers;e.focus?(t.removeEventListener("focus",t.$_ptooltipFocusEvent),t.$_ptooltipFocusEvent=null,t.removeEventListener("blur",t.$_ptooltipBlurEvent),t.$_ptooltipBlurEvent=null):(t.removeEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),t.$_ptooltipMouseEnterEvent=null,t.removeEventListener("mouseleave",t.$_ptooltipMouseLeaveEvent),t.$_ptooltipMouseLeaveEvent=null,t.removeEventListener("click",t.$_ptooltipClickEvent),t.$_ptooltipClickEvent=null),t.removeEventListener("keydown",t.$_ptooltipKeydownEvent),window.removeEventListener("resize",t.$_pWindowResizeEvent),t.$_ptooltipId&&this.remove(t)},bindScrollListener:function(t){var e=this;t.$_ptooltipScrollHandler||(t.$_ptooltipScrollHandler=new j(t,function(){e.hide(t)})),t.$_ptooltipScrollHandler.bindScrollListener()},unbindScrollListener:function(t){t.$_ptooltipScrollHandler&&t.$_ptooltipScrollHandler.unbindScrollListener()},onMouseEnter:function(t,e){var n=t.currentTarget,i=n.$_ptooltipShowDelay;this.show(n,e,i)},onMouseLeave:function(t){var e=t.currentTarget,n=e.$_ptooltipHideDelay,i=e.$_ptooltipAutoHide;if(i)this.hide(e,n);else{var r=h(t.target,"data-pc-name")==="tooltip"||h(t.target,"data-pc-section")==="arrow"||h(t.target,"data-pc-section")==="text"||h(t.relatedTarget,"data-pc-name")==="tooltip"||h(t.relatedTarget,"data-pc-section")==="arrow"||h(t.relatedTarget,"data-pc-section")==="text";!r&&this.hide(e,n)}},onFocus:function(t,e){var n=t.currentTarget,i=n.$_ptooltipShowDelay;this.show(n,e,i)},onBlur:function(t){var e=t.currentTarget,n=e.$_ptooltipHideDelay;this.hide(e,n)},onClick:function(t){var e=t.currentTarget,n=e.$_ptooltipHideDelay;this.hide(e,n)},onKeydown:function(t){var e=t.currentTarget,n=e.$_ptooltipHideDelay;t.code==="Escape"&&this.hide(t.currentTarget,n)},onWindowResize:function(t){K()||this.hide(t),window.removeEventListener("resize",t.$_pWindowResizeEvent)},tooltipActions:function(t,e){if(!(t.$_ptooltipDisabled||!N(t)||!t.$_ptooltipPendingShow)){t.$_ptooltipPendingShow=!1,this.remove(t);var n=this.create(t,e);this.align(t),!this.isUnstyled()&&Y(n,250);var i=this;window.addEventListener("resize",t.$_pWindowResizeEvent),n.addEventListener("mouseleave",function r(){i.hide(t),n.removeEventListener("mouseleave",r),t.removeEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),setTimeout(function(){return t.addEventListener("mouseenter",t.$_ptooltipMouseEnterEvent)},50)}),this.bindScrollListener(t),b.set("tooltip",n,t.$_ptooltipZIndex)}},show:function(t,e,n){var i=this;clearTimeout(t.$_ptooltipShowTimer),clearTimeout(t.$_ptooltipHideTimer),n!==void 0?(t.$_ptooltipShowTimer=setTimeout(function(){return i.tooltipActions(t,e)},n),t.$_ptooltipPendingShow=!0):(this.tooltipActions(t,e),t.$_ptooltipPendingShow=!1)},tooltipRemoval:function(t){this.remove(t),this.unbindScrollListener(t),window.removeEventListener("resize",t.$_pWindowResizeEvent)},hide:function(t,e){var n=this;clearTimeout(t.$_ptooltipShowTimer),clearTimeout(t.$_ptooltipHideTimer),t.$_ptooltipPendingShow=!1,e!==void 0?t.$_ptooltipHideTimer=setTimeout(function(){return n.tooltipRemoval(t)},e):this.tooltipRemoval(t)},getTooltipElement:function(t){return document.getElementById(t.$_ptooltipId)},getArrowElement:function(t){var e=this.getTooltipElement(t);return B(e,'[data-pc-section="arrow"]')},create:function(t){var e=t.$_ptooltipModifiers,n=k("div",{class:!this.isUnstyled()&&this.cx("arrow"),"p-bind":this.ptm("arrow",{context:e})}),i=k("div",{class:!this.isUnstyled()&&this.cx("text"),"p-bind":this.ptm("text",{context:e})});t.$_ptooltipEscape?(i.innerHTML="",i.appendChild(document.createTextNode(t.$_ptooltipValue))):i.innerHTML=t.$_ptooltipValue;var r=k("div",x(x({id:t.$_ptooltipIdAttr,role:"tooltip",style:{display:"inline-block",width:t.$_ptooltipFitContent?"fit-content":void 0,pointerEvents:!this.isUnstyled()&&t.$_ptooltipAutoHide&&"none"},class:[!this.isUnstyled()&&this.cx("root"),t.$_ptooltipClass]},this.$attrSelector,""),"p-bind",this.ptm("root",{context:e})),n,i);return document.body.appendChild(r),t.$_ptooltipId=r.id,this.$el=r,r},remove:function(t){if(t){var e=this.getTooltipElement(t);e&&e.parentElement&&(b.clear(e),document.body.removeChild(e)),t.$_ptooltipId=null}},align:function(t){var e=t.$_ptooltipModifiers;e.top?(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignTop(t))):e.left?(this.alignLeft(t),this.isOutOfBounds(t)&&(this.alignRight(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignLeft(t))))):e.bottom?(this.alignBottom(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&this.alignBottom(t))):(this.alignRight(t),this.isOutOfBounds(t)&&(this.alignLeft(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignRight(t)))))},getHostOffset:function(t){var e=t.getBoundingClientRect(),n=e.left+V(),i=e.top+Z();return{left:n,top:i}},alignRight:function(t){this.preAlign(t,"right");var e=this.getTooltipElement(t),n=this.getArrowElement(t),i=this.getHostOffset(t),r=i.left+c(t),s=i.top+(f(t)-f(e))/2;e.style.left=r+"px",e.style.top=s+"px",n.style.top="50%",n.style.right=null,n.style.bottom=null,n.style.left="0"},alignLeft:function(t){this.preAlign(t,"left");var e=this.getTooltipElement(t),n=this.getArrowElement(t),i=this.getHostOffset(t),r=i.left-c(e),s=i.top+(f(t)-f(e))/2;e.style.left=r+"px",e.style.top=s+"px",n.style.top="50%",n.style.right="0",n.style.bottom=null,n.style.left=null},alignTop:function(t){this.preAlign(t,"top");var e=this.getTooltipElement(t),n=this.getArrowElement(t),i=c(e),r=c(t),s=$(),d=s.width,l=this.getHostOffset(t),a=l.left+(r-i)/2,g=l.top-f(e);a<0?a=0:a+i>d&&(a=Math.floor(l.left+r-i)),e.style.left=a+"px",e.style.top=g+"px";var L=l.left-this.getHostOffset(e).left+r/2;n.style.top=null,n.style.right=null,n.style.bottom="0",n.style.left=L+"px"},alignBottom:function(t){this.preAlign(t,"bottom");var e=this.getTooltipElement(t),n=this.getArrowElement(t),i=c(e),r=c(t),s=$(),d=s.width,l=this.getHostOffset(t),a=l.left+(r-i)/2,g=l.top+f(t);a<0?a=0:a+i>d&&(a=Math.floor(l.left+r-i)),e.style.left=a+"px",e.style.top=g+"px";var L=l.left-this.getHostOffset(e).left+r/2;n.style.top="0",n.style.right=null,n.style.bottom=null,n.style.left=L+"px"},preAlign:function(t,e){var n=this.getTooltipElement(t);n.style.left="-999px",n.style.top="-999px",F(n,"p-tooltip-".concat(n.$_ptooltipPosition)),!this.isUnstyled()&&M(n,"p-tooltip-".concat(e)),n.$_ptooltipPosition=e,n.setAttribute("data-p-position",e)},isOutOfBounds:function(t){var e=this.getTooltipElement(t),n=e.getBoundingClientRect(),i=n.top,r=n.left,s=c(e),d=f(e),l=$();return r+s>l.width||r<0||i<0||i+d>l.height},getTarget:function(t){var e;return U(t,"p-inputwrapper")&&(e=B(t,"input"))!==null&&e!==void 0?e:t},getModifiers:function(t){return t.modifiers&&Object.keys(t.modifiers).length?t.modifiers:t.arg&&u(t.arg)==="object"?Object.entries(t.arg).reduce(function(e,n){var i=mt(n,2),r=i[0],s=i[1];return(r==="event"||r==="position")&&(e[s]=!0),e},{}):{}}}}),Tt=`
    .p-tag {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: dt('tag.primary.background');
        color: dt('tag.primary.color');
        font-size: dt('tag.font.size');
        font-weight: dt('tag.font.weight');
        padding: dt('tag.padding');
        border-radius: dt('tag.border.radius');
        gap: dt('tag.gap');
    }

    .p-tag-icon {
        font-size: dt('tag.icon.size');
        width: dt('tag.icon.size');
        height: dt('tag.icon.size');
    }

    .p-tag-rounded {
        border-radius: dt('tag.rounded.border.radius');
    }

    .p-tag-success {
        background: dt('tag.success.background');
        color: dt('tag.success.color');
    }

    .p-tag-info {
        background: dt('tag.info.background');
        color: dt('tag.info.color');
    }

    .p-tag-warn {
        background: dt('tag.warn.background');
        color: dt('tag.warn.color');
    }

    .p-tag-danger {
        background: dt('tag.danger.background');
        color: dt('tag.danger.color');
    }

    .p-tag-secondary {
        background: dt('tag.secondary.background');
        color: dt('tag.secondary.color');
    }

    .p-tag-contrast {
        background: dt('tag.contrast.background');
        color: dt('tag.contrast.color');
    }
`,Ot={root:function(t){var e=t.props;return["p-tag p-component",{"p-tag-info":e.severity==="info","p-tag-success":e.severity==="success","p-tag-warn":e.severity==="warn","p-tag-danger":e.severity==="danger","p-tag-secondary":e.severity==="secondary","p-tag-contrast":e.severity==="contrast","p-tag-rounded":e.rounded}]},icon:"p-tag-icon",label:"p-tag-label"},St=z.extend({name:"tag",style:Tt,classes:Ot}),zt={name:"BaseTag",extends:P,props:{value:null,severity:null,rounded:Boolean,icon:String},style:St,provide:function(){return{$pcTag:this,$parentInstance:this}}};function m(o){"@babel/helpers - typeof";return m=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},m(o)}function At(o,t,e){return(t=Bt(t))in o?Object.defineProperty(o,t,{value:e,enumerable:!0,configurable:!0,writable:!0}):o[t]=e,o}function Bt(o){var t=Ht(o,"string");return m(t)=="symbol"?t:t+""}function Ht(o,t){if(m(o)!="object"||!o)return o;var e=o[Symbol.toPrimitive];if(e!==void 0){var n=e.call(o,t);if(m(n)!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(o)}var W={name:"Tag",extends:zt,inheritAttrs:!1,computed:{dataP:function(){return Q(At({rounded:this.rounded},this.severity,this.severity))}}},Rt=["data-p"];function Dt(o,t,e,n,i,r){return p(),y("span",v({class:o.cx("root"),"data-p":r.dataP},o.ptmi("root")),[o.$slots.icon?(p(),A(X(o.$slots.icon),v({key:0,class:o.cx("icon")},o.ptm("icon")),null,16,["class"])):o.icon?(p(),y("span",v({key:1,class:[o.cx("icon"),o.icon]},o.ptm("icon")),null,16)):_("",!0),o.value!=null||o.$slots.default?T(o.$slots,"default",{key:2},function(){return[O("span",v({class:o.cx("label")},o.ptm("label")),G(o.value),17)]}):_("",!0)],16,Rt)}W.render=Dt;var xt=`
    .p-popover {
        margin-block-start: dt('popover.gutter');
        background: dt('popover.background');
        color: dt('popover.color');
        border: 1px solid dt('popover.border.color');
        border-radius: dt('popover.border.radius');
        box-shadow: dt('popover.shadow');
        will-change: transform;
    }

    .p-popover-content {
        padding: dt('popover.content.padding');
    }

    .p-popover-flipped {
        margin-block-start: calc(dt('popover.gutter') * -1);
        margin-block-end: dt('popover.gutter');
    }

    .p-popover:after,
    .p-popover:before {
        bottom: 100%;
        left: calc(dt('popover.arrow.offset') + dt('popover.arrow.left'));
        content: ' ';
        height: 0;
        width: 0;
        position: absolute;
        pointer-events: none;
    }

    .p-popover:after {
        border-width: calc(dt('popover.gutter') - 2px);
        margin-left: calc(-1 * (dt('popover.gutter') - 2px));
        border-style: solid;
        border-color: transparent;
        border-bottom-color: dt('popover.background');
    }

    .p-popover:before {
        border-width: dt('popover.gutter');
        margin-left: calc(-1 * dt('popover.gutter'));
        border-style: solid;
        border-color: transparent;
        border-bottom-color: dt('popover.border.color');
    }

    .p-popover-flipped:after,
    .p-popover-flipped:before {
        bottom: auto;
        top: 100%;
    }

    .p-popover.p-popover-flipped:after {
        border-bottom-color: transparent;
        border-top-color: dt('popover.background');
    }

    .p-popover.p-popover-flipped:before {
        border-bottom-color: transparent;
        border-top-color: dt('popover.border.color');
    }
`,Mt={root:"p-popover p-component",content:"p-popover-content"},Kt=z.extend({name:"popover",style:xt,classes:Mt}),Pt={name:"BasePopover",extends:P,props:{dismissable:{type:Boolean,default:!0},appendTo:{type:[String,Object],default:"body"},baseZIndex:{type:Number,default:0},autoZIndex:{type:Boolean,default:!0},breakpoints:{type:Object,default:null},closeOnEscape:{type:Boolean,default:!0}},style:Kt,provide:function(){return{$pcPopover:this,$parentInstance:this}}},It={name:"Popover",extends:Pt,inheritAttrs:!1,emits:["show","hide"],data:function(){return{visible:!1}},watch:{dismissable:{immediate:!0,handler:function(t){t?this.bindOutsideClickListener():this.unbindOutsideClickListener()}}},selfClick:!1,target:null,eventTarget:null,outsideClickListener:null,scrollHandler:null,resizeListener:null,container:null,styleElement:null,overlayEventListener:null,documentKeydownListener:null,contentResizeObserver:null,beforeUnmount:function(){this.dismissable&&this.unbindOutsideClickListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.destroyStyle(),this.unbindResizeListener(),this.unbindContentResizeListener(),this.target=null,this.container&&this.autoZIndex&&b.clear(this.container),this.overlayEventListener&&(E.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null),this.container=null},mounted:function(){this.breakpoints&&this.createStyle()},methods:{toggle:function(t,e){this.visible?this.hide():this.show(t,e)},show:function(t,e){this.visible=!0,this.eventTarget=t.currentTarget,this.target=e||t.currentTarget},hide:function(){this.visible=!1},onContentClick:function(){this.selfClick=!0},onEnter:function(t){var e=this;lt(t,{position:"absolute",top:"0"}),this.alignOverlay(),this.dismissable&&this.bindOutsideClickListener(),this.bindScrollListener(),this.bindResizeListener(),this.autoZIndex&&b.set("overlay",t,this.baseZIndex||this.$primevue.config.zIndex.overlay),this.overlayEventListener=function(n){e.container.contains(n.target)&&(e.selfClick=!0)},this.bindContentResizeListener(),this.focus(),E.on("overlay-click",this.overlayEventListener),this.$emit("show"),this.closeOnEscape&&this.bindDocumentKeyDownListener()},onLeave:function(){this.unbindOutsideClickListener(),this.unbindScrollListener(),this.unbindResizeListener(),this.unbindDocumentKeyDownListener(),this.unbindContentResizeListener(),E.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null,this.$emit("hide")},onAfterLeave:function(t){this.autoZIndex&&b.clear(t)},alignOverlay:function(){rt(this.container,this.target,!1);var t=R(this.container),e=R(this.target),n=0;t.left<e.left&&(n=e.left-t.left),this.container.style.setProperty(st("popover.arrow.left").name,"".concat(n,"px")),t.top<e.top&&(this.container.setAttribute("data-p-popover-flipped","true"),!this.isUnstyled&&M(this.container,"p-popover-flipped"))},onContentKeydown:function(t){t.code==="Escape"&&this.closeOnEscape&&(this.hide(),it(this.target))},onButtonKeydown:function(t){switch(t.code){case"ArrowDown":case"ArrowUp":case"ArrowLeft":case"ArrowRight":t.preventDefault()}},focus:function(){var t=this.container.querySelector("[autofocus]");t&&t.focus()},onKeyDown:function(t){t.code==="Escape"&&this.closeOnEscape&&(this.visible=!1)},bindDocumentKeyDownListener:function(){this.documentKeydownListener||(this.documentKeydownListener=this.onKeyDown.bind(this),window.document.addEventListener("keydown",this.documentKeydownListener))},unbindDocumentKeyDownListener:function(){this.documentKeydownListener&&(window.document.removeEventListener("keydown",this.documentKeydownListener),this.documentKeydownListener=null)},bindOutsideClickListener:function(){var t=this;!this.outsideClickListener&&nt()&&(this.outsideClickListener=function(e){t.visible&&!t.selfClick&&!t.isTargetClicked(e)&&(t.visible=!1),t.selfClick=!1},document.addEventListener("click",this.outsideClickListener))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener),this.outsideClickListener=null,this.selfClick=!1)},bindScrollListener:function(){var t=this;this.scrollHandler||(this.scrollHandler=new j(this.target,function(){t.visible&&(t.visible=!1)})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var t=this;this.resizeListener||(this.resizeListener=function(){t.visible&&!K()&&(t.visible=!1)},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},bindContentResizeListener:function(){var t=this;this.contentResizeObserver||(this.contentResizeObserver=new ResizeObserver(function(){t.visible&&t.alignOverlay()}),this.contentResizeObserver.observe(this.container))},unbindContentResizeListener:function(){this.contentResizeObserver&&(this.contentResizeObserver.disconnect(),this.contentResizeObserver=null)},isTargetClicked:function(t){return this.eventTarget&&(this.eventTarget===t.target||this.eventTarget.contains(t.target))},containerRef:function(t){this.container=t},createStyle:function(){if(!this.styleElement&&!this.isUnstyled){var t;this.styleElement=document.createElement("style"),this.styleElement.type="text/css",ot(this.styleElement,"nonce",(t=this.$primevue)===null||t===void 0||(t=t.config)===null||t===void 0||(t=t.csp)===null||t===void 0?void 0:t.nonce),document.head.appendChild(this.styleElement);var e="";for(var n in this.breakpoints)e+=`
                        @media screen and (max-width: `.concat(n,`) {
                            .p-popover[`).concat(this.$attrSelector,`] {
                                width: `).concat(this.breakpoints[n],` !important;
                            }
                        }
                    `);this.styleElement.innerHTML=e}},destroyStyle:function(){this.styleElement&&(document.head.removeChild(this.styleElement),this.styleElement=null)},onOverlayClick:function(t){E.emit("overlay-click",{originalEvent:t,target:this.target})}},directives:{focustrap:et,ripple:tt},components:{Portal:J}},jt=["aria-modal"];function Wt(o,t,e,n,i,r){var s=at("Portal"),d=dt("focustrap");return p(),A(s,{appendTo:o.appendTo},{default:S(function(){return[pt(ut,v({name:"p-anchored-overlay",onEnter:r.onEnter,onLeave:r.onLeave,onAfterLeave:r.onAfterLeave},o.ptm("transition")),{default:S(function(){return[i.visible?I((p(),y("div",v({key:0,ref:r.containerRef,role:"dialog","aria-modal":i.visible,onClick:t[3]||(t[3]=function(){return r.onOverlayClick&&r.onOverlayClick.apply(r,arguments)}),class:o.cx("root")},o.ptmi("root")),[o.$slots.container?T(o.$slots,"container",{key:0,closeCallback:r.hide,keydownCallback:function(a){return r.onButtonKeydown(a)}}):(p(),y("div",v({key:1,class:o.cx("content"),onClick:t[0]||(t[0]=function(){return r.onContentClick&&r.onContentClick.apply(r,arguments)}),onMousedown:t[1]||(t[1]=function(){return r.onContentClick&&r.onContentClick.apply(r,arguments)}),onKeydown:t[2]||(t[2]=function(){return r.onContentKeydown&&r.onContentKeydown.apply(r,arguments)})},o.ptm("content")),[T(o.$slots,"default")],16))],16,jt)),[[d]]):_("",!0)]}),_:3},16,["onEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo"])}It.render=Wt;const Ut={class:"sys-badge__inner"},Ft={key:0,class:"sys-badge__label"},Vt=ct({__name:"SysBadge",props:{customized:{type:Boolean},iconOnly:{type:Boolean}},setup(o){const{t}=ft();return(e,n)=>{const i=Ct;return I((p(),A(C(W),{severity:o.customized?"warn":"secondary",class:"sys-badge"},{default:S(()=>[O("span",Ut,[n[0]||(n[0]=O("i",{class:"pi pi-briefcase","aria-hidden":"true"},null,-1)),o.iconOnly?_("",!0):(p(),y("span",Ft,"SYS"))])]),_:1},8,["severity"])),[[i,o.customized?C(t)("template.builtinCustomized"):C(t)("template.sysTooltip"),void 0,{top:!0}]])}}}),Yt=vt(Vt,[["__scopeId","data-v-09cbbd7d"]]);export{Yt as S,Ct as T,It as a,W as s};
