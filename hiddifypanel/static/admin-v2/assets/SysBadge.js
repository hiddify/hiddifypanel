import{B,an as P,T as k,a5 as u,ao as c,ap as w,aq as W,ar as z,as as j,at as F,a7 as h,au as _,av as U,aw as V,a3 as R,ax as f,ay as m,az as O,aA as Z,Z as N,R as q,aB as Y,s as G,aC as Q,aD as J,a2 as X,a6 as tt,aE as T,aF as et,a8 as ot,j as it,h as nt,o as b,q as D,v as $,G as rt,ae as st,a as E,w as M,c as C,r as S,e as K,D as lt,E as at,H as L,i as x,_ as dt}from"./index.js";import{C as I,O as g}from"./index2.js";import{s as pt}from"./index4.js";var ut=`
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
`,ct={root:"p-tooltip p-component",arrow:"p-tooltip-arrow",text:"p-tooltip-text"},ft=B.extend({name:"tooltip-directive",style:ut,classes:ct}),vt=Z.extend({style:ft});function ht(i,t){return yt(i)||gt(i,t)||mt(i,t)||bt()}function bt(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function mt(i,t){if(i){if(typeof i=="string")return A(i,t);var e={}.toString.call(i).slice(8,-1);return e==="Object"&&i.constructor&&(e=i.constructor.name),e==="Map"||e==="Set"?Array.from(i):e==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(e)?A(i,t):void 0}}function A(i,t){(t==null||t>i.length)&&(t=i.length);for(var e=0,o=Array(t);e<t;e++)o[e]=i[e];return o}function gt(i,t){var e=i==null?null:typeof Symbol<"u"&&i[Symbol.iterator]||i["@@iterator"];if(e!=null){var o,n,r,s,d=[],l=!0,a=!1;try{if(r=(e=e.call(i)).next,t!==0)for(;!(l=(o=r.call(e)).done)&&(d.push(o.value),d.length!==t);l=!0);}catch(v){a=!0,n=v}finally{try{if(!l&&e.return!=null&&(s=e.return(),Object(s)!==s))return}finally{if(a)throw n}}return d}}function yt(i){if(Array.isArray(i))return i}function H(i,t,e){return(t=wt(t))in i?Object.defineProperty(i,t,{value:e,enumerable:!0,configurable:!0,writable:!0}):i[t]=e,i}function wt(i){var t=_t(i,"string");return p(t)=="symbol"?t:t+""}function _t(i,t){if(p(i)!="object"||!i)return i;var e=i[Symbol.toPrimitive];if(e!==void 0){var o=e.call(i,t);if(p(o)!="object")return o;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(i)}function p(i){"@babel/helpers - typeof";return p=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},p(i)}var Et=vt.extend("tooltip",{beforeMount:function(t,e){var o,n=this.getTarget(t);if(n.$_ptooltipModifiers=this.getModifiers(e),e.value){if(typeof e.value=="string")n.$_ptooltipValue=e.value,n.$_ptooltipDisabled=!1,n.$_ptooltipEscape=!0,n.$_ptooltipClass=null,n.$_ptooltipFitContent=!0,n.$_ptooltipIdAttr=m("pv_id")+"_tooltip",n.$_ptooltipShowDelay=0,n.$_ptooltipHideDelay=0,n.$_ptooltipAutoHide=!0;else if(p(e.value)==="object"&&e.value){if(O(e.value.value)||e.value.value.trim()==="")return;n.$_ptooltipValue=e.value.value,n.$_ptooltipDisabled=!!e.value.disabled===e.value.disabled?e.value.disabled:!1,n.$_ptooltipEscape=!!e.value.escape===e.value.escape?e.value.escape:!0,n.$_ptooltipClass=e.value.class||"",n.$_ptooltipFitContent=!!e.value.fitContent===e.value.fitContent?e.value.fitContent:!0,n.$_ptooltipIdAttr=e.value.id||m("pv_id")+"_tooltip",n.$_ptooltipShowDelay=e.value.showDelay||0,n.$_ptooltipHideDelay=e.value.hideDelay||0,n.$_ptooltipAutoHide=!!e.value.autoHide===e.value.autoHide?e.value.autoHide:!0}}else return;n.$_ptooltipZIndex=(o=e.instance.$primevue)===null||o===void 0||(o=o.config)===null||o===void 0||(o=o.zIndex)===null||o===void 0?void 0:o.tooltip,this.bindEvents(n,e),t.setAttribute("data-pd-tooltip",!0)},updated:function(t,e){var o=this.getTarget(t);if(o.$_ptooltipModifiers=this.getModifiers(e),this.unbindEvents(o),!!e.value){if(typeof e.value=="string")o.$_ptooltipValue=e.value,o.$_ptooltipDisabled=!1,o.$_ptooltipEscape=!0,o.$_ptooltipClass=null,o.$_ptooltipIdAttr=o.$_ptooltipIdAttr||m("pv_id")+"_tooltip",o.$_ptooltipShowDelay=0,o.$_ptooltipHideDelay=0,o.$_ptooltipAutoHide=!0,this.bindEvents(o,e);else if(p(e.value)==="object"&&e.value)if(O(e.value.value)||e.value.value.trim()===""){this.unbindEvents(o,e);return}else o.$_ptooltipValue=e.value.value,o.$_ptooltipDisabled=!!e.value.disabled===e.value.disabled?e.value.disabled:!1,o.$_ptooltipEscape=!!e.value.escape===e.value.escape?e.value.escape:!0,o.$_ptooltipClass=e.value.class||"",o.$_ptooltipFitContent=!!e.value.fitContent===e.value.fitContent?e.value.fitContent:!0,o.$_ptooltipIdAttr=e.value.id||o.$_ptooltipIdAttr||m("pv_id")+"_tooltip",o.$_ptooltipShowDelay=e.value.showDelay||0,o.$_ptooltipHideDelay=e.value.hideDelay||0,o.$_ptooltipAutoHide=!!e.value.autoHide===e.value.autoHide?e.value.autoHide:!0,this.bindEvents(o,e)}},unmounted:function(t,e){var o=this.getTarget(t);this.hide(t,0),this.remove(o),this.unbindEvents(o,e),o.$_ptooltipScrollHandler&&(o.$_ptooltipScrollHandler.destroy(),o.$_ptooltipScrollHandler=null)},methods:{bindEvents:function(t,e){var o=this,n=t.$_ptooltipModifiers;n.focus?(t.$_ptooltipFocusEvent=function(r){return o.onFocus(r,e)},t.$_ptooltipBlurEvent=this.onBlur.bind(this),t.addEventListener("focus",t.$_ptooltipFocusEvent),t.addEventListener("blur",t.$_ptooltipBlurEvent)):(t.$_ptooltipMouseEnterEvent=function(r){return o.onMouseEnter(r,e)},t.$_ptooltipMouseLeaveEvent=this.onMouseLeave.bind(this),t.$_ptooltipClickEvent=this.onClick.bind(this),t.addEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),t.addEventListener("mouseleave",t.$_ptooltipMouseLeaveEvent),t.addEventListener("click",t.$_ptooltipClickEvent)),t.$_ptooltipKeydownEvent=this.onKeydown.bind(this),t.addEventListener("keydown",t.$_ptooltipKeydownEvent),t.$_pWindowResizeEvent=this.onWindowResize.bind(this,t)},unbindEvents:function(t){var e=t.$_ptooltipModifiers;e.focus?(t.removeEventListener("focus",t.$_ptooltipFocusEvent),t.$_ptooltipFocusEvent=null,t.removeEventListener("blur",t.$_ptooltipBlurEvent),t.$_ptooltipBlurEvent=null):(t.removeEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),t.$_ptooltipMouseEnterEvent=null,t.removeEventListener("mouseleave",t.$_ptooltipMouseLeaveEvent),t.$_ptooltipMouseLeaveEvent=null,t.removeEventListener("click",t.$_ptooltipClickEvent),t.$_ptooltipClickEvent=null),t.removeEventListener("keydown",t.$_ptooltipKeydownEvent),window.removeEventListener("resize",t.$_pWindowResizeEvent),t.$_ptooltipId&&this.remove(t)},bindScrollListener:function(t){var e=this;t.$_ptooltipScrollHandler||(t.$_ptooltipScrollHandler=new I(t,function(){e.hide(t)})),t.$_ptooltipScrollHandler.bindScrollListener()},unbindScrollListener:function(t){t.$_ptooltipScrollHandler&&t.$_ptooltipScrollHandler.unbindScrollListener()},onMouseEnter:function(t,e){var o=t.currentTarget,n=o.$_ptooltipShowDelay;this.show(o,e,n)},onMouseLeave:function(t){var e=t.currentTarget,o=e.$_ptooltipHideDelay,n=e.$_ptooltipAutoHide;if(n)this.hide(e,o);else{var r=f(t.target,"data-pc-name")==="tooltip"||f(t.target,"data-pc-section")==="arrow"||f(t.target,"data-pc-section")==="text"||f(t.relatedTarget,"data-pc-name")==="tooltip"||f(t.relatedTarget,"data-pc-section")==="arrow"||f(t.relatedTarget,"data-pc-section")==="text";!r&&this.hide(e,o)}},onFocus:function(t,e){var o=t.currentTarget,n=o.$_ptooltipShowDelay;this.show(o,e,n)},onBlur:function(t){var e=t.currentTarget,o=e.$_ptooltipHideDelay;this.hide(e,o)},onClick:function(t){var e=t.currentTarget,o=e.$_ptooltipHideDelay;this.hide(e,o)},onKeydown:function(t){var e=t.currentTarget,o=e.$_ptooltipHideDelay;t.code==="Escape"&&this.hide(t.currentTarget,o)},onWindowResize:function(t){R()||this.hide(t),window.removeEventListener("resize",t.$_pWindowResizeEvent)},tooltipActions:function(t,e){if(!(t.$_ptooltipDisabled||!U(t)||!t.$_ptooltipPendingShow)){t.$_ptooltipPendingShow=!1,this.remove(t);var o=this.create(t,e);this.align(t),!this.isUnstyled()&&V(o,250);var n=this;window.addEventListener("resize",t.$_pWindowResizeEvent),o.addEventListener("mouseleave",function r(){n.hide(t),o.removeEventListener("mouseleave",r),t.removeEventListener("mouseenter",t.$_ptooltipMouseEnterEvent),setTimeout(function(){return t.addEventListener("mouseenter",t.$_ptooltipMouseEnterEvent)},50)}),this.bindScrollListener(t),h.set("tooltip",o,t.$_ptooltipZIndex)}},show:function(t,e,o){var n=this;clearTimeout(t.$_ptooltipShowTimer),clearTimeout(t.$_ptooltipHideTimer),o!==void 0?(t.$_ptooltipShowTimer=setTimeout(function(){return n.tooltipActions(t,e)},o),t.$_ptooltipPendingShow=!0):(this.tooltipActions(t,e),t.$_ptooltipPendingShow=!1)},tooltipRemoval:function(t){this.remove(t),this.unbindScrollListener(t),window.removeEventListener("resize",t.$_pWindowResizeEvent)},hide:function(t,e){var o=this;clearTimeout(t.$_ptooltipShowTimer),clearTimeout(t.$_ptooltipHideTimer),t.$_ptooltipPendingShow=!1,e!==void 0?t.$_ptooltipHideTimer=setTimeout(function(){return o.tooltipRemoval(t)},e):this.tooltipRemoval(t)},getTooltipElement:function(t){return document.getElementById(t.$_ptooltipId)},getArrowElement:function(t){var e=this.getTooltipElement(t);return k(e,'[data-pc-section="arrow"]')},create:function(t){var e=t.$_ptooltipModifiers,o=_("div",{class:!this.isUnstyled()&&this.cx("arrow"),"p-bind":this.ptm("arrow",{context:e})}),n=_("div",{class:!this.isUnstyled()&&this.cx("text"),"p-bind":this.ptm("text",{context:e})});t.$_ptooltipEscape?(n.innerHTML="",n.appendChild(document.createTextNode(t.$_ptooltipValue))):n.innerHTML=t.$_ptooltipValue;var r=_("div",H(H({id:t.$_ptooltipIdAttr,role:"tooltip",style:{display:"inline-block",width:t.$_ptooltipFitContent?"fit-content":void 0,pointerEvents:!this.isUnstyled()&&t.$_ptooltipAutoHide&&"none"},class:[!this.isUnstyled()&&this.cx("root"),t.$_ptooltipClass]},this.$attrSelector,""),"p-bind",this.ptm("root",{context:e})),o,n);return document.body.appendChild(r),t.$_ptooltipId=r.id,this.$el=r,r},remove:function(t){if(t){var e=this.getTooltipElement(t);e&&e.parentElement&&(h.clear(e),document.body.removeChild(e)),t.$_ptooltipId=null}},align:function(t){var e=t.$_ptooltipModifiers;e.top?(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignTop(t))):e.left?(this.alignLeft(t),this.isOutOfBounds(t)&&(this.alignRight(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignLeft(t))))):e.bottom?(this.alignBottom(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&this.alignBottom(t))):(this.alignRight(t),this.isOutOfBounds(t)&&(this.alignLeft(t),this.isOutOfBounds(t)&&(this.alignTop(t),this.isOutOfBounds(t)&&(this.alignBottom(t),this.isOutOfBounds(t)&&this.alignRight(t)))))},getHostOffset:function(t){var e=t.getBoundingClientRect(),o=e.left+j(),n=e.top+F();return{left:o,top:n}},alignRight:function(t){this.preAlign(t,"right");var e=this.getTooltipElement(t),o=this.getArrowElement(t),n=this.getHostOffset(t),r=n.left+u(t),s=n.top+(c(t)-c(e))/2;e.style.left=r+"px",e.style.top=s+"px",o.style.top="50%",o.style.right=null,o.style.bottom=null,o.style.left="0"},alignLeft:function(t){this.preAlign(t,"left");var e=this.getTooltipElement(t),o=this.getArrowElement(t),n=this.getHostOffset(t),r=n.left-u(e),s=n.top+(c(t)-c(e))/2;e.style.left=r+"px",e.style.top=s+"px",o.style.top="50%",o.style.right="0",o.style.bottom=null,o.style.left=null},alignTop:function(t){this.preAlign(t,"top");var e=this.getTooltipElement(t),o=this.getArrowElement(t),n=u(e),r=u(t),s=w(),d=s.width,l=this.getHostOffset(t),a=l.left+(r-n)/2,v=l.top-c(e);a<0?a=0:a+n>d&&(a=Math.floor(l.left+r-n)),e.style.left=a+"px",e.style.top=v+"px";var y=l.left-this.getHostOffset(e).left+r/2;o.style.top=null,o.style.right=null,o.style.bottom="0",o.style.left=y+"px"},alignBottom:function(t){this.preAlign(t,"bottom");var e=this.getTooltipElement(t),o=this.getArrowElement(t),n=u(e),r=u(t),s=w(),d=s.width,l=this.getHostOffset(t),a=l.left+(r-n)/2,v=l.top+c(t);a<0?a=0:a+n>d&&(a=Math.floor(l.left+r-n)),e.style.left=a+"px",e.style.top=v+"px";var y=l.left-this.getHostOffset(e).left+r/2;o.style.top="0",o.style.right=null,o.style.bottom=null,o.style.left=y+"px"},preAlign:function(t,e){var o=this.getTooltipElement(t);o.style.left="-999px",o.style.top="-999px",W(o,"p-tooltip-".concat(o.$_ptooltipPosition)),!this.isUnstyled()&&z(o,"p-tooltip-".concat(e)),o.$_ptooltipPosition=e,o.setAttribute("data-p-position",e)},isOutOfBounds:function(t){var e=this.getTooltipElement(t),o=e.getBoundingClientRect(),n=o.top,r=o.left,s=u(e),d=c(e),l=w();return r+s>l.width||r<0||n<0||n+d>l.height},getTarget:function(t){var e;return P(t,"p-inputwrapper")&&(e=k(t,"input"))!==null&&e!==void 0?e:t},getModifiers:function(t){return t.modifiers&&Object.keys(t.modifiers).length?t.modifiers:t.arg&&p(t.arg)==="object"?Object.entries(t.arg).reduce(function(e,o){var n=ht(o,2),r=n[0],s=n[1];return(r==="event"||r==="position")&&(e[s]=!0),e},{}):{}}}}),Lt=`
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
`,$t={root:"p-popover p-component",content:"p-popover-content"},Ct=B.extend({name:"popover",style:Lt,classes:$t}),kt={name:"BasePopover",extends:G,props:{dismissable:{type:Boolean,default:!0},appendTo:{type:[String,Object],default:"body"},baseZIndex:{type:Number,default:0},autoZIndex:{type:Boolean,default:!0},breakpoints:{type:Object,default:null},closeOnEscape:{type:Boolean,default:!0}},style:Ct,provide:function(){return{$pcPopover:this,$parentInstance:this}}},Ot={name:"Popover",extends:kt,inheritAttrs:!1,emits:["show","hide"],data:function(){return{visible:!1}},watch:{dismissable:{immediate:!0,handler:function(t){t?this.bindOutsideClickListener():this.unbindOutsideClickListener()}}},selfClick:!1,target:null,eventTarget:null,outsideClickListener:null,scrollHandler:null,resizeListener:null,container:null,styleElement:null,overlayEventListener:null,documentKeydownListener:null,contentResizeObserver:null,beforeUnmount:function(){this.dismissable&&this.unbindOutsideClickListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.destroyStyle(),this.unbindResizeListener(),this.unbindContentResizeListener(),this.target=null,this.container&&this.autoZIndex&&h.clear(this.container),this.overlayEventListener&&(g.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null),this.container=null},mounted:function(){this.breakpoints&&this.createStyle()},methods:{toggle:function(t,e){this.visible?this.hide():this.show(t,e)},show:function(t,e){this.visible=!0,this.eventTarget=t.currentTarget,this.target=e||t.currentTarget},hide:function(){this.visible=!1},onContentClick:function(){this.selfClick=!0},onEnter:function(t){var e=this;ot(t,{position:"absolute",top:"0"}),this.alignOverlay(),this.dismissable&&this.bindOutsideClickListener(),this.bindScrollListener(),this.bindResizeListener(),this.autoZIndex&&h.set("overlay",t,this.baseZIndex||this.$primevue.config.zIndex.overlay),this.overlayEventListener=function(o){e.container.contains(o.target)&&(e.selfClick=!0)},this.bindContentResizeListener(),this.focus(),g.on("overlay-click",this.overlayEventListener),this.$emit("show"),this.closeOnEscape&&this.bindDocumentKeyDownListener()},onLeave:function(){this.unbindOutsideClickListener(),this.unbindScrollListener(),this.unbindResizeListener(),this.unbindDocumentKeyDownListener(),this.unbindContentResizeListener(),g.off("overlay-click",this.overlayEventListener),this.overlayEventListener=null,this.$emit("hide")},onAfterLeave:function(t){this.autoZIndex&&h.clear(t)},alignOverlay:function(){tt(this.container,this.target,!1);var t=T(this.container),e=T(this.target),o=0;t.left<e.left&&(o=e.left-t.left),this.container.style.setProperty(et("popover.arrow.left").name,"".concat(o,"px")),t.top<e.top&&(this.container.setAttribute("data-p-popover-flipped","true"),!this.isUnstyled&&z(this.container,"p-popover-flipped"))},onContentKeydown:function(t){t.code==="Escape"&&this.closeOnEscape&&(this.hide(),X(this.target))},onButtonKeydown:function(t){switch(t.code){case"ArrowDown":case"ArrowUp":case"ArrowLeft":case"ArrowRight":t.preventDefault()}},focus:function(){var t=this.container.querySelector("[autofocus]");t&&t.focus()},onKeyDown:function(t){t.code==="Escape"&&this.closeOnEscape&&(this.visible=!1)},bindDocumentKeyDownListener:function(){this.documentKeydownListener||(this.documentKeydownListener=this.onKeyDown.bind(this),window.document.addEventListener("keydown",this.documentKeydownListener))},unbindDocumentKeyDownListener:function(){this.documentKeydownListener&&(window.document.removeEventListener("keydown",this.documentKeydownListener),this.documentKeydownListener=null)},bindOutsideClickListener:function(){var t=this;!this.outsideClickListener&&J()&&(this.outsideClickListener=function(e){t.visible&&!t.selfClick&&!t.isTargetClicked(e)&&(t.visible=!1),t.selfClick=!1},document.addEventListener("click",this.outsideClickListener))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener),this.outsideClickListener=null,this.selfClick=!1)},bindScrollListener:function(){var t=this;this.scrollHandler||(this.scrollHandler=new I(this.target,function(){t.visible&&(t.visible=!1)})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var t=this;this.resizeListener||(this.resizeListener=function(){t.visible&&!R()&&(t.visible=!1)},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},bindContentResizeListener:function(){var t=this;this.contentResizeObserver||(this.contentResizeObserver=new ResizeObserver(function(){t.visible&&t.alignOverlay()}),this.contentResizeObserver.observe(this.container))},unbindContentResizeListener:function(){this.contentResizeObserver&&(this.contentResizeObserver.disconnect(),this.contentResizeObserver=null)},isTargetClicked:function(t){return this.eventTarget&&(this.eventTarget===t.target||this.eventTarget.contains(t.target))},containerRef:function(t){this.container=t},createStyle:function(){if(!this.styleElement&&!this.isUnstyled){var t;this.styleElement=document.createElement("style"),this.styleElement.type="text/css",Q(this.styleElement,"nonce",(t=this.$primevue)===null||t===void 0||(t=t.config)===null||t===void 0||(t=t.csp)===null||t===void 0?void 0:t.nonce),document.head.appendChild(this.styleElement);var e="";for(var o in this.breakpoints)e+=`
                        @media screen and (max-width: `.concat(o,`) {
                            .p-popover[`).concat(this.$attrSelector,`] {
                                width: `).concat(this.breakpoints[o],` !important;
                            }
                        }
                    `);this.styleElement.innerHTML=e}},destroyStyle:function(){this.styleElement&&(document.head.removeChild(this.styleElement),this.styleElement=null)},onOverlayClick:function(t){g.emit("overlay-click",{originalEvent:t,target:this.target})}},directives:{focustrap:Y,ripple:q},components:{Portal:N}},Tt=["aria-modal"];function St(i,t,e,o,n,r){var s=it("Portal"),d=nt("focustrap");return b(),D(s,{appendTo:i.appendTo},{default:$(function(){return[rt(st,E({name:"p-anchored-overlay",onEnter:r.onEnter,onLeave:r.onLeave,onAfterLeave:r.onAfterLeave},i.ptm("transition")),{default:$(function(){return[n.visible?M((b(),C("div",E({key:0,ref:r.containerRef,role:"dialog","aria-modal":n.visible,onClick:t[3]||(t[3]=function(){return r.onOverlayClick&&r.onOverlayClick.apply(r,arguments)}),class:i.cx("root")},i.ptmi("root")),[i.$slots.container?S(i.$slots,"container",{key:0,closeCallback:r.hide,keydownCallback:function(a){return r.onButtonKeydown(a)}}):(b(),C("div",E({key:1,class:i.cx("content"),onClick:t[0]||(t[0]=function(){return r.onContentClick&&r.onContentClick.apply(r,arguments)}),onMousedown:t[1]||(t[1]=function(){return r.onContentClick&&r.onContentClick.apply(r,arguments)}),onKeydown:t[2]||(t[2]=function(){return r.onContentKeydown&&r.onContentKeydown.apply(r,arguments)})},i.ptm("content")),[S(i.$slots,"default")],16))],16,Tt)),[[d]]):K("",!0)]}),_:3},16,["onEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo"])}Ot.render=St;const xt={class:"sys-badge__inner"},At={key:0,class:"sys-badge__label"},Ht=lt({__name:"SysBadge",props:{customized:{type:Boolean},iconOnly:{type:Boolean}},setup(i){const{t}=at();return(e,o)=>{const n=Et;return M((b(),D(L(pt),{severity:i.customized?"warn":"secondary",class:"sys-badge"},{default:$(()=>[x("span",xt,[o[0]||(o[0]=x("i",{class:"pi pi-briefcase","aria-hidden":"true"},null,-1)),i.iconOnly?K("",!0):(b(),C("span",At,"SYS"))])]),_:1},8,["severity"])),[[n,i.customized?L(t)("template.builtinCustomized"):L(t)("template.sysTooltip"),void 0,{top:!0}]])}}}),Dt=dt(Ht,[["__scopeId","data-v-09cbbd7d"]]);export{Dt as S,Et as T,Ot as s};
