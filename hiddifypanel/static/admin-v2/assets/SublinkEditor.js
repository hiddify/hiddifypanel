import{B as z,i as j,o as f,c as v,k as O,g as m,s as $t,e as S,R as ct,j as et,aW as _,aX as wt,M as H,O as xt,aa as D,N as kt,aw as st,ad as ft,v as J,p as k,q as M,l as B,am as pt,a8 as Tt,a0 as F,w as $,n as bt,F as V,x as Bt,d as Pt,aR as St,u as Ct,f as P,b as d,D as ot,aS as it,A as q,C as Q,a as h,h as lt,E as dt,_ as Ot}from"./index.js";import{s as At}from"./index8.js";import{s as It}from"./index7.js";import{a as Ut,s as T}from"./index6.js";import{_ as C}from"./HorizontalField.vue_vue_type_script_setup_true_lang.js";var Vt=`
    .p-tabs {
        display: flex;
        flex-direction: column;
    }

    .p-tablist {
        display: flex;
        position: relative;
        overflow: hidden;
        background: dt('tabs.tablist.background');
    }

    .p-tablist-viewport {
        overflow-x: auto;
        overflow-y: hidden;
        scroll-behavior: smooth;
        scrollbar-width: none;
        overscroll-behavior: contain auto;
    }

    .p-tablist-viewport::-webkit-scrollbar {
        display: none;
    }

    .p-tablist-tab-list {
        position: relative;
        display: flex;
        border-style: solid;
        border-color: dt('tabs.tablist.border.color');
        border-width: dt('tabs.tablist.border.width');
    }

    .p-tablist-content {
        flex-grow: 1;
    }

    .p-tablist-nav-button {
        all: unset;
        position: absolute !important;
        flex-shrink: 0;
        inset-block-start: 0;
        z-index: 2;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: dt('tabs.nav.button.background');
        color: dt('tabs.nav.button.color');
        width: dt('tabs.nav.button.width');
        transition:
            color dt('tabs.transition.duration'),
            outline-color dt('tabs.transition.duration'),
            box-shadow dt('tabs.transition.duration');
        box-shadow: dt('tabs.nav.button.shadow');
        outline-color: transparent;
        cursor: pointer;
    }

    .p-tablist-nav-button:focus-visible {
        z-index: 1;
        box-shadow: dt('tabs.nav.button.focus.ring.shadow');
        outline: dt('tabs.nav.button.focus.ring.width') dt('tabs.nav.button.focus.ring.style') dt('tabs.nav.button.focus.ring.color');
        outline-offset: dt('tabs.nav.button.focus.ring.offset');
    }

    .p-tablist-nav-button:hover {
        color: dt('tabs.nav.button.hover.color');
    }

    .p-tablist-prev-button {
        inset-inline-start: 0;
    }

    .p-tablist-next-button {
        inset-inline-end: 0;
    }

    .p-tablist-prev-button:dir(rtl),
    .p-tablist-next-button:dir(rtl) {
        transform: rotate(180deg);
    }

    .p-tab {
        flex-shrink: 0;
        cursor: pointer;
        user-select: none;
        position: relative;
        border-style: solid;
        white-space: nowrap;
        gap: dt('tabs.tab.gap');
        background: dt('tabs.tab.background');
        border-width: dt('tabs.tab.border.width');
        border-color: dt('tabs.tab.border.color');
        color: dt('tabs.tab.color');
        padding: dt('tabs.tab.padding');
        font-weight: dt('tabs.tab.font.weight');
        transition:
            background dt('tabs.transition.duration'),
            border-color dt('tabs.transition.duration'),
            color dt('tabs.transition.duration'),
            outline-color dt('tabs.transition.duration'),
            box-shadow dt('tabs.transition.duration');
        margin: dt('tabs.tab.margin');
        outline-color: transparent;
    }

    .p-tab:not(.p-disabled):focus-visible {
        z-index: 1;
        box-shadow: dt('tabs.tab.focus.ring.shadow');
        outline: dt('tabs.tab.focus.ring.width') dt('tabs.tab.focus.ring.style') dt('tabs.tab.focus.ring.color');
        outline-offset: dt('tabs.tab.focus.ring.offset');
    }

    .p-tab:not(.p-tab-active):not(.p-disabled):hover {
        background: dt('tabs.tab.hover.background');
        border-color: dt('tabs.tab.hover.border.color');
        color: dt('tabs.tab.hover.color');
    }

    .p-tab-active {
        background: dt('tabs.tab.active.background');
        border-color: dt('tabs.tab.active.border.color');
        color: dt('tabs.tab.active.color');
    }

    .p-tabpanels {
        background: dt('tabs.tabpanel.background');
        color: dt('tabs.tabpanel.color');
        padding: dt('tabs.tabpanel.padding');
        outline: 0 none;
    }

    .p-tabpanel:focus-visible {
        box-shadow: dt('tabs.tabpanel.focus.ring.shadow');
        outline: dt('tabs.tabpanel.focus.ring.width') dt('tabs.tabpanel.focus.ring.style') dt('tabs.tabpanel.focus.ring.color');
        outline-offset: dt('tabs.tabpanel.focus.ring.offset');
    }

    .p-tablist-active-bar {
        z-index: 1;
        display: block;
        position: absolute;
        inset-block-end: dt('tabs.active.bar.bottom');
        height: dt('tabs.active.bar.height');
        background: dt('tabs.active.bar.background');
        transition: 250ms cubic-bezier(0.35, 0, 0.25, 1);
    }
`,Lt={root:function(e){var a=e.props;return["p-tabs p-component",{"p-tabs-scrollable":a.scrollable}]}},zt=z.extend({name:"tabs",style:Vt,classes:Lt}),Nt={name:"BaseTabs",extends:j,props:{value:{type:[String,Number],default:void 0},lazy:{type:Boolean,default:!1},scrollable:{type:Boolean,default:!1},showNavigators:{type:Boolean,default:!0},tabindex:{type:Number,default:0},selectOnFocus:{type:Boolean,default:!1}},style:zt,provide:function(){return{$pcTabs:this,$parentInstance:this}}},Et={name:"Tabs",extends:Nt,inheritAttrs:!1,emits:["update:value"],data:function(){return{d_value:this.value}},watch:{value:function(e){this.d_value=e}},methods:{updateValue:function(e){this.d_value!==e&&(this.d_value=e,this.$emit("update:value",e))},isVertical:function(){return this.orientation==="vertical"}}};function Rt(t,e,a,n,s,r){return f(),v("div",m({class:t.cx("root")},t.ptmi("root")),[O(t.$slots,"default")],16)}Et.render=Rt;var ht={name:"ChevronLeftIcon",extends:$t};function Kt(t){return Ft(t)||Dt(t)||Wt(t)||jt()}function jt(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Wt(t,e){if(t){if(typeof t=="string")return X(t,e);var a={}.toString.call(t).slice(8,-1);return a==="Object"&&t.constructor&&(a=t.constructor.name),a==="Map"||a==="Set"?Array.from(t):a==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(a)?X(t,e):void 0}}function Dt(t){if(typeof Symbol<"u"&&t[Symbol.iterator]!=null||t["@@iterator"]!=null)return Array.from(t)}function Ft(t){if(Array.isArray(t))return X(t)}function X(t,e){(e==null||e>t.length)&&(e=t.length);for(var a=0,n=Array(e);a<e;a++)n[a]=t[a];return n}function Ht(t,e,a,n,s,r){return f(),v("svg",m({width:"14",height:"14",viewBox:"0 0 14 14",fill:"none",xmlns:"http://www.w3.org/2000/svg"},t.pti()),Kt(e[0]||(e[0]=[S("path",{d:"M9.61296 13C9.50997 13.0005 9.40792 12.9804 9.3128 12.9409C9.21767 12.9014 9.13139 12.8433 9.05902 12.7701L3.83313 7.54416C3.68634 7.39718 3.60388 7.19795 3.60388 6.99022C3.60388 6.78249 3.68634 6.58325 3.83313 6.43628L9.05902 1.21039C9.20762 1.07192 9.40416 0.996539 9.60724 1.00012C9.81032 1.00371 10.0041 1.08597 10.1477 1.22959C10.2913 1.37322 10.3736 1.56698 10.3772 1.77005C10.3808 1.97313 10.3054 2.16968 10.1669 2.31827L5.49496 6.99022L10.1669 11.6622C10.3137 11.8091 10.3962 12.0084 10.3962 12.2161C10.3962 12.4238 10.3137 12.6231 10.1669 12.7701C10.0945 12.8433 10.0083 12.9014 9.91313 12.9409C9.81801 12.9804 9.71596 13.0005 9.61296 13Z",fill:"currentColor"},null,-1)])),16)}ht.render=Ht;var Jt={root:"p-tablist",content:"p-tablist-content p-tablist-viewport",tabList:"p-tablist-tab-list",activeBar:"p-tablist-active-bar",prevButton:"p-tablist-prev-button p-tablist-nav-button",nextButton:"p-tablist-next-button p-tablist-nav-button"},Mt=z.extend({name:"tablist",classes:Jt}),_t={name:"BaseTabList",extends:j,props:{},style:Mt,provide:function(){return{$pcTabList:this,$parentInstance:this}}},qt={name:"TabList",extends:_t,inheritAttrs:!1,inject:["$pcTabs"],data:function(){return{isPrevButtonEnabled:!1,isNextButtonEnabled:!0}},resizeObserver:void 0,inkBarObserver:void 0,watch:{showNavigators:function(e){e?this.bindResizeObserver():this.unbindResizeObserver()},activeValue:{flush:"post",handler:function(){this.updateInkBar(),this.bindInkBarObserver()}}},mounted:function(){var e=this;setTimeout(function(){e.updateInkBar(),e.bindInkBarObserver()},150),this.showNavigators&&(this.updateButtonState(),this.bindResizeObserver())},updated:function(){this.showNavigators&&this.updateButtonState()},beforeUnmount:function(){this.unbindResizeObserver(),this.unbindInkBarObserver()},methods:{onScroll:function(e){this.showNavigators&&this.updateButtonState(),e.preventDefault()},onPrevButtonClick:function(){var e=this.$refs.content,a=this.getVisibleButtonWidths(),n=_(e)-a,s=Math.abs(e.scrollLeft),r=n*.8,i=s-r,p=Math.max(i,0);e.scrollLeft=st(e)?-1*p:p},onNextButtonClick:function(){var e=this.$refs.content,a=this.getVisibleButtonWidths(),n=_(e)-a,s=Math.abs(e.scrollLeft),r=n*.8,i=s+r,p=e.scrollWidth-n,g=Math.min(i,p);e.scrollLeft=st(e)?-1*g:g},bindResizeObserver:function(){var e=this;this.resizeObserver=new ResizeObserver(function(){return e.updateButtonState()}),this.resizeObserver.observe(this.$refs.list)},unbindResizeObserver:function(){var e;(e=this.resizeObserver)===null||e===void 0||e.unobserve(this.$refs.list),this.resizeObserver=void 0},bindInkBarObserver:function(){var e=this;this.unbindInkBarObserver();var a=this.$refs.content,n=H(a,'[data-pc-name="tab"][data-p-active="true"]');n&&(this.inkBarObserver=new ResizeObserver(function(){return e.updateInkBar()}),this.inkBarObserver.observe(n))},unbindInkBarObserver:function(){var e;(e=this.inkBarObserver)===null||e===void 0||e.disconnect(),this.inkBarObserver=void 0},updateInkBar:function(){var e=this.$refs,a=e.content,n=e.inkbar,s=e.tabs;if(n){var r=H(a,'[data-pc-name="tab"][data-p-active="true"]');this.$pcTabs.isVertical()?(n.style.height=xt(r)+"px",n.style.top=D(r).top-D(s).top+"px"):(n.style.width=kt(r)+"px",n.style.left=D(r).left-D(s).left+"px")}},updateButtonState:function(){var e=this.$refs,a=e.list,n=e.content,s=n.scrollTop,r=n.scrollWidth,i=n.scrollHeight,p=n.offsetWidth,g=n.offsetHeight,y=Math.abs(n.scrollLeft),x=[_(n),wt(n)],w=x[0],I=x[1];this.$pcTabs.isVertical()?(this.isPrevButtonEnabled=s!==0,this.isNextButtonEnabled=a.offsetHeight>=g&&parseInt(s)!==i-I):(this.isPrevButtonEnabled=y!==0,this.isNextButtonEnabled=a.offsetWidth>=p&&parseInt(y)!==r-w)},getVisibleButtonWidths:function(){var e=this.$refs,a=e.prevButton,n=e.nextButton,s=0;return this.showNavigators&&(s=((a==null?void 0:a.offsetWidth)||0)+((n==null?void 0:n.offsetWidth)||0)),s}},computed:{templates:function(){return this.$pcTabs.$slots},activeValue:function(){return this.$pcTabs.d_value},showNavigators:function(){return this.$pcTabs.showNavigators},prevButtonAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.previous:void 0},nextButtonAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.next:void 0},dataP:function(){return et({scrollable:this.$pcTabs.scrollable})}},components:{ChevronLeftIcon:ht,ChevronRightIcon:At},directives:{ripple:ct}},Qt=["data-p"],Xt=["aria-label","tabindex"],Zt=["data-p"],Gt=["aria-orientation"],Yt=["aria-label","tabindex"];function te(t,e,a,n,s,r){var i=ft("ripple");return f(),v("div",m({ref:"list",class:t.cx("root"),"data-p":r.dataP},t.ptmi("root")),[r.showNavigators&&s.isPrevButtonEnabled?J((f(),v("button",m({key:0,ref:"prevButton",type:"button",class:t.cx("prevButton"),"aria-label":r.prevButtonAriaLabel,tabindex:r.$pcTabs.tabindex,onClick:e[0]||(e[0]=function(){return r.onPrevButtonClick&&r.onPrevButtonClick.apply(r,arguments)})},t.ptm("prevButton"),{"data-pc-group-section":"navigator"}),[(f(),k(M(r.templates.previcon||"ChevronLeftIcon"),m({"aria-hidden":"true"},t.ptm("prevIcon")),null,16))],16,Xt)),[[i]]):B("",!0),S("div",m({ref:"content",class:t.cx("content"),onScroll:e[1]||(e[1]=function(){return r.onScroll&&r.onScroll.apply(r,arguments)}),"data-p":r.dataP},t.ptm("content")),[S("div",m({ref:"tabs",class:t.cx("tabList"),role:"tablist","aria-orientation":r.$pcTabs.orientation||"horizontal"},t.ptm("tabList")),[O(t.$slots,"default"),S("span",m({ref:"inkbar",class:t.cx("activeBar"),role:"presentation","aria-hidden":"true"},t.ptm("activeBar")),null,16)],16,Gt)],16,Zt),r.showNavigators&&s.isNextButtonEnabled?J((f(),v("button",m({key:1,ref:"nextButton",type:"button",class:t.cx("nextButton"),"aria-label":r.nextButtonAriaLabel,tabindex:r.$pcTabs.tabindex,onClick:e[2]||(e[2]=function(){return r.onNextButtonClick&&r.onNextButtonClick.apply(r,arguments)})},t.ptm("nextButton"),{"data-pc-group-section":"navigator"}),[(f(),k(M(r.templates.nexticon||"ChevronRightIcon"),m({"aria-hidden":"true"},t.ptm("nextIcon")),null,16))],16,Yt)),[[i]]):B("",!0)],16,Qt)}qt.render=te;var ee={root:function(e){var a=e.instance,n=e.props;return["p-tab",{"p-tab-active":a.active,"p-disabled":n.disabled}]}},ae=z.extend({name:"tab",classes:ee}),ne={name:"BaseTab",extends:j,props:{value:{type:[String,Number],default:void 0},disabled:{type:Boolean,default:!1},as:{type:[String,Object],default:"BUTTON"},asChild:{type:Boolean,default:!1}},style:ae,provide:function(){return{$pcTab:this,$parentInstance:this}}},re={name:"Tab",extends:ne,inheritAttrs:!1,inject:["$pcTabs","$pcTabList"],methods:{onFocus:function(){this.$pcTabs.selectOnFocus&&this.changeActiveValue()},onClick:function(){this.changeActiveValue()},onKeydown:function(e){switch(e.code){case"ArrowRight":this.onArrowRightKey(e);break;case"ArrowLeft":this.onArrowLeftKey(e);break;case"Home":this.onHomeKey(e);break;case"End":this.onEndKey(e);break;case"PageDown":this.onPageDownKey(e);break;case"PageUp":this.onPageUpKey(e);break;case"Enter":case"NumpadEnter":case"Space":this.onEnterKey(e);break}},onArrowRightKey:function(e){var a=this.findNextTab(e.currentTarget);a?this.changeFocusedTab(e,a):this.onHomeKey(e),e.preventDefault()},onArrowLeftKey:function(e){var a=this.findPrevTab(e.currentTarget);a?this.changeFocusedTab(e,a):this.onEndKey(e),e.preventDefault()},onHomeKey:function(e){var a=this.findFirstTab();this.changeFocusedTab(e,a),e.preventDefault()},onEndKey:function(e){var a=this.findLastTab();this.changeFocusedTab(e,a),e.preventDefault()},onPageDownKey:function(e){this.scrollInView(this.findLastTab()),e.preventDefault()},onPageUpKey:function(e){this.scrollInView(this.findFirstTab()),e.preventDefault()},onEnterKey:function(e){this.changeActiveValue()},findNextTab:function(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,n=a?e:e.nextElementSibling;return n?F(n,"data-p-disabled")||F(n,"data-pc-section")==="activebar"?this.findNextTab(n):H(n,'[data-pc-name="tab"]'):null},findPrevTab:function(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,n=a?e:e.previousElementSibling;return n?F(n,"data-p-disabled")||F(n,"data-pc-section")==="activebar"?this.findPrevTab(n):H(n,'[data-pc-name="tab"]'):null},findFirstTab:function(){return this.findNextTab(this.$pcTabList.$refs.tabs.firstElementChild,!0)},findLastTab:function(){return this.findPrevTab(this.$pcTabList.$refs.tabs.lastElementChild,!0)},changeActiveValue:function(){this.$pcTabs.updateValue(this.value)},changeFocusedTab:function(e,a){Tt(a),this.scrollInView(a)},scrollInView:function(e){var a;e==null||(a=e.scrollIntoView)===null||a===void 0||a.call(e,{block:"nearest"})}},computed:{active:function(){var e;return pt((e=this.$pcTabs)===null||e===void 0?void 0:e.d_value,this.value)},id:function(){var e;return"".concat((e=this.$pcTabs)===null||e===void 0?void 0:e.$id,"_tab_").concat(this.value)},ariaControls:function(){var e;return"".concat((e=this.$pcTabs)===null||e===void 0?void 0:e.$id,"_tabpanel_").concat(this.value)},attrs:function(){return m(this.asAttrs,this.a11yAttrs,this.ptmi("root",this.ptParams))},asAttrs:function(){return this.as==="BUTTON"?{type:"button",disabled:this.disabled}:void 0},a11yAttrs:function(){return{id:this.id,tabindex:this.active?this.$pcTabs.tabindex:-1,role:"tab","aria-selected":this.active,"aria-controls":this.ariaControls,"data-pc-name":"tab","data-p-disabled":this.disabled,"data-p-active":this.active,onFocus:this.onFocus,onKeydown:this.onKeydown}},ptParams:function(){return{context:{active:this.active}}},dataP:function(){return et({active:this.active})}},directives:{ripple:ct}};function se(t,e,a,n,s,r){var i=ft("ripple");return t.asChild?O(t.$slots,"default",{key:1,dataP:r.dataP,class:bt(t.cx("root")),active:r.active,a11yAttrs:r.a11yAttrs,onClick:r.onClick}):J((f(),k(M(t.as),m({key:0,class:t.cx("root"),"data-p":r.dataP,onClick:r.onClick},r.attrs),{default:$(function(){return[O(t.$slots,"default")]}),_:3},16,["class","data-p","onClick"])),[[i]])}re.render=se;var oe={root:"p-tabpanels"},ie=z.extend({name:"tabpanels",classes:oe}),le={name:"BaseTabPanels",extends:j,props:{},style:ie,provide:function(){return{$pcTabPanels:this,$parentInstance:this}}},de={name:"TabPanels",extends:le,inheritAttrs:!1};function ue(t,e,a,n,s,r){return f(),v("div",m({class:t.cx("root"),role:"presentation"},t.ptmi("root")),[O(t.$slots,"default")],16)}de.render=ue;var ce={root:function(e){var a=e.instance;return["p-tabpanel",{"p-tabpanel-active":a.active}]}},fe=z.extend({name:"tabpanel",classes:ce}),pe={name:"BaseTabPanel",extends:j,props:{value:{type:[String,Number],default:void 0},as:{type:[String,Object],default:"DIV"},asChild:{type:Boolean,default:!1},header:null,headerStyle:null,headerClass:null,headerProps:null,headerActionProps:null,contentStyle:null,contentClass:null,contentProps:null,disabled:Boolean},style:fe,provide:function(){return{$pcTabPanel:this,$parentInstance:this}}},be={name:"TabPanel",extends:pe,inheritAttrs:!1,inject:["$pcTabs"],computed:{active:function(){var e;return pt((e=this.$pcTabs)===null||e===void 0?void 0:e.d_value,this.value)},id:function(){var e;return"".concat((e=this.$pcTabs)===null||e===void 0?void 0:e.$id,"_tabpanel_").concat(this.value)},ariaLabelledby:function(){var e;return"".concat((e=this.$pcTabs)===null||e===void 0?void 0:e.$id,"_tab_").concat(this.value)},attrs:function(){return m(this.a11yAttrs,this.ptmi("root",this.ptParams))},a11yAttrs:function(){var e;return{id:this.id,tabindex:(e=this.$pcTabs)===null||e===void 0?void 0:e.tabindex,role:"tabpanel","aria-labelledby":this.ariaLabelledby,"data-pc-name":"tabpanel","data-p-active":this.active}},ptParams:function(){return{context:{active:this.active}}}}};function he(t,e,a,n,s,r){var i,p;return r.$pcTabs?(f(),v(V,{key:1},[t.asChild?O(t.$slots,"default",{key:1,class:bt(t.cx("root")),active:r.active,a11yAttrs:r.a11yAttrs}):(f(),v(V,{key:0},[!((i=r.$pcTabs)!==null&&i!==void 0&&i.lazy)||r.active?J((f(),k(M(t.as),m({key:0,class:t.cx("root")},r.attrs),{default:$(function(){return[O(t.$slots,"default")]}),_:3},16,["class"])),[[Bt,(p=r.$pcTabs)!==null&&p!==void 0&&p.lazy?!0:r.active]]):B("",!0)],64))],64)):O(t.$slots,"default",{key:0})}be.render=he;var ve=`
    .p-textarea {
        font-family: inherit;
        font-feature-settings: inherit;
        font-size: 1rem;
        color: dt('textarea.color');
        background: dt('textarea.background');
        padding-block: dt('textarea.padding.y');
        padding-inline: dt('textarea.padding.x');
        border: 1px solid dt('textarea.border.color');
        transition:
            background dt('textarea.transition.duration'),
            color dt('textarea.transition.duration'),
            border-color dt('textarea.transition.duration'),
            outline-color dt('textarea.transition.duration'),
            box-shadow dt('textarea.transition.duration');
        appearance: none;
        border-radius: dt('textarea.border.radius');
        outline-color: transparent;
        box-shadow: dt('textarea.shadow');
    }

    .p-textarea:enabled:hover {
        border-color: dt('textarea.hover.border.color');
    }

    .p-textarea:enabled:focus {
        border-color: dt('textarea.focus.border.color');
        box-shadow: dt('textarea.focus.ring.shadow');
        outline: dt('textarea.focus.ring.width') dt('textarea.focus.ring.style') dt('textarea.focus.ring.color');
        outline-offset: dt('textarea.focus.ring.offset');
    }

    .p-textarea.p-invalid {
        border-color: dt('textarea.invalid.border.color');
    }

    .p-textarea.p-variant-filled {
        background: dt('textarea.filled.background');
    }

    .p-textarea.p-variant-filled:enabled:hover {
        background: dt('textarea.filled.hover.background');
    }

    .p-textarea.p-variant-filled:enabled:focus {
        background: dt('textarea.filled.focus.background');
    }

    .p-textarea:disabled {
        opacity: 1;
        background: dt('textarea.disabled.background');
        color: dt('textarea.disabled.color');
    }

    .p-textarea::placeholder {
        color: dt('textarea.placeholder.color');
    }

    .p-textarea.p-invalid::placeholder {
        color: dt('textarea.invalid.placeholder.color');
    }

    .p-textarea-fluid {
        width: 100%;
    }

    .p-textarea-resizable {
        overflow: hidden;
        resize: none;
    }

    .p-textarea-sm {
        font-size: dt('textarea.sm.font.size');
        padding-block: dt('textarea.sm.padding.y');
        padding-inline: dt('textarea.sm.padding.x');
    }

    .p-textarea-lg {
        font-size: dt('textarea.lg.font.size');
        padding-block: dt('textarea.lg.padding.y');
        padding-inline: dt('textarea.lg.padding.x');
    }
`,me={root:function(e){var a=e.instance,n=e.props;return["p-textarea p-component",{"p-filled":a.$filled,"p-textarea-resizable ":n.autoResize,"p-textarea-sm p-inputfield-sm":n.size==="small","p-textarea-lg p-inputfield-lg":n.size==="large","p-invalid":a.$invalid,"p-variant-filled":a.$variant==="filled","p-textarea-fluid":a.$fluid}]}},ye=z.extend({name:"textarea",style:ve,classes:me}),ge={name:"BaseTextarea",extends:Ut,props:{autoResize:Boolean},style:ye,provide:function(){return{$pcTextarea:this,$parentInstance:this}}};function K(t){"@babel/helpers - typeof";return K=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(e){return typeof e}:function(e){return e&&typeof Symbol=="function"&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},K(t)}function $e(t,e,a){return(e=we(e))in t?Object.defineProperty(t,e,{value:a,enumerable:!0,configurable:!0,writable:!0}):t[e]=a,t}function we(t){var e=xe(t,"string");return K(e)=="symbol"?e:e+""}function xe(t,e){if(K(t)!="object"||!t)return t;var a=t[Symbol.toPrimitive];if(a!==void 0){var n=a.call(t,e);if(K(n)!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(e==="string"?String:Number)(t)}var Z={name:"Textarea",extends:ge,inheritAttrs:!1,observer:null,mounted:function(){var e=this;this.autoResize&&(this.observer=new ResizeObserver(function(){requestAnimationFrame(function(){e.resize()})}),this.observer.observe(this.$el))},updated:function(){this.autoResize&&this.resize()},beforeUnmount:function(){this.observer&&this.observer.disconnect()},methods:{resize:function(){if(this.$el.offsetParent){var e=this.$el.style.height,a=parseInt(e)||0,n=this.$el.scrollHeight,s=!a||n>a,r=a&&n<a;r?(this.$el.style.height="auto",this.$el.style.height="".concat(this.$el.scrollHeight,"px")):s&&(this.$el.style.height="".concat(n,"px"))}},onInput:function(e){this.autoResize&&this.resize(),this.writeValue(e.target.value,e)}},computed:{attrs:function(){return m(this.ptmi("root",{context:{filled:this.$filled,disabled:this.disabled}}),this.formField)},dataP:function(){return et($e({invalid:this.$invalid,fluid:this.$fluid,filled:this.$variant==="filled"},this.size,this.size))}}},ke=["value","name","disabled","aria-invalid","data-p"];function Te(t,e,a,n,s,r){return f(),v("textarea",m({class:t.cx("root"),value:t.d_value,name:t.name,disabled:t.disabled,"aria-invalid":t.invalid||void 0,"data-p":r.dataP,onInput:e[0]||(e[0]=function(){return r.onInput&&r.onInput.apply(r,arguments)})},r.attrs),null,16,ke)}Z.render=Te;function Be(t){let e="";for(const a of t)e+=String.fromCharCode(a);return e}function Pe(t){const e=new Uint8Array(t.length);for(let a=0;a<t.length;a++)e[a]=t.charCodeAt(a);return e}function vt(t,e=!1){const a=btoa(Be(new TextEncoder().encode(t)));return e?a.replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,""):a}function at(t){const e=t.replace(/\s+/g,"");if(!e)return"";const a=e.replace(/-/g,"+").replace(/_/g,"/"),n=a+"=".repeat((4-a.length%4)%4);return new TextDecoder().decode(Pe(atob(n)))}function mt(t){try{return at(t)}catch{return null}}function ra(t){return encodeURIComponent(t)}function sa(t){return decodeURIComponent(t.replace(/\+/g,"%20"))}function L(t){try{return decodeURIComponent(t.replace(/\+/g,"%20"))}catch{return t}}const G=/^[a-z][a-z0-9+.-]*:\/\//i,Se=new Set(["trojan","hysteria","hysteria2","hy2","tuic","anytls","ss","shadowsocks"]);function yt(t){return t.kind==="error"}function nt(t){return t.kind==="vmess"}function R(t){return t.kind==="uri"}function Y(t){const e=t.trim();return e.startsWith("{")&&e.endsWith("}")||e.startsWith("[")&&e.endsWith("]")}function Ce(t){const e=t.trim();if(!Y(e))return t;try{return JSON.stringify(JSON.parse(e),null,2)}catch{return t}}function Oe(t){let e=L(t);if(!Y(e.trim())){const a=L(e);Y(a.trim())&&(e=a)}return Ce(e)}function Ae(t){const e=t.trim();if(!e)return null;try{return encodeURIComponent(JSON.stringify(JSON.parse(e)))}catch{return encodeURIComponent(e)}}function Ie(t,e){const a=[];let n=e;for(const r of t){const i=r.key.trim();if(i){if(i==="extra"){n.trim()||(n=r.value);continue}a.push(`${encodeURIComponent(i)}=${encodeURIComponent(r.value)}`)}}const s=Ae(n);return s!=null&&a.push(`extra=${s}`),a.join("&")}function rt(t){const e=t.indexOf("#");return e<0?{body:t,fragment:""}:{body:t.slice(0,e),fragment:L(t.slice(e+1))}}function Ue(t){const e=t.lastIndexOf("@");return e<0?{hostport:t}:{userinfo:t.slice(0,e),hostport:t.slice(e+1)}}function Ve(t){let e=t;if(e.startsWith("[")){const i=e.indexOf("]");if(i<0)return{server:e,port:"",path:""};const p=e.slice(1,i);e=e.slice(i+1);let g="",y="";if(e.startsWith(":")){const x=e.indexOf("/");g=x>=0?e.slice(1,x):e.slice(1),x>=0&&(y=e.slice(x))}else e.startsWith("/")&&(y=e);return{server:p,port:g,path:y}}const a=e.indexOf("/"),n=a>=0?e.slice(0,a):e,s=a>=0?e.slice(a):"",r=n.lastIndexOf(":");return r>=0?{server:n.slice(0,r),port:n.slice(r+1),path:s}:{server:n,port:"",path:s}}function tt(t,e){const a=L(t),n=a.indexOf(":");return n>=0?{user:a.slice(0,n),password:a.slice(n+1)}:Se.has(e)?{user:"",password:a}:{user:a,password:""}}function Le(t,e){const a=t&&e?`${t}:${e}`:t||e;if(!a)return{user:"",password:"",method:""};const n=mt(a)??a,s=n.indexOf(":");return s>0&&/^[a-z0-9+-]+$/i.test(n.slice(0,s))?{user:"",password:n.slice(s+1),method:n.slice(0,s)}:tt(a,"ss")}function ze(t){const e=[];let a="";if(!t)return{params:e,extra:a};for(const n of t.split("&")){if(!n)continue;const s=n.indexOf("="),r=L(s>=0?n.slice(0,s):n);if(!r)continue;const i=s>=0?L(n.slice(s+1)):"";r==="extra"?a=Oe(i):e.push({key:r,value:i})}return{params:e,extra:a}}function Ne(t){const{body:e}=rt(t),a=at(e),n=JSON.parse(a);if(!n||typeof n!="object"||Array.isArray(n))throw new Error("vmess payload is not an object");return{kind:"vmess",protocol:"vmess",json:JSON.stringify(n,null,2)}}function ut(t,e){const{body:a,fragment:n}=rt(e),s=a.indexOf("?"),r=s>=0?a.slice(0,s):a,{params:i,extra:p}=ze(s>=0?a.slice(s+1):""),{userinfo:g,hostport:y}=Ue(r),{server:x,port:w,path:I}=Ve(y);let N="",E="",W="";if(g)if(t==="ss"){const c=tt(g,"ss"),b=Le(c.user,c.password);N=b.user,E=b.password,W=b.method}else{const c=tt(g,t);N=c.user,E=c.password}return{kind:"uri",protocol:t,server:x,port:w,user:N,password:E,path:I,fragment:n,method:W,params:i,extra:p}}function Ee(t){const e=t.trim(),a=e.match(G);if(!a)return{kind:"error",error:"Not a share link",raw:e};const n=a[0].slice(0,-3).toLowerCase(),s=e.slice(a[0].length);try{if(n==="vmess")return Ne(s);if(n==="ss"&&!s.includes("@")){const{body:r,fragment:i}=rt(s),p=at(r);if(p.includes("@"))return ut("ss",i?`${p}#${encodeURIComponent(i)}`:p)}return ut(n,s)}catch(r){return{kind:"error",error:r instanceof Error?r.message:String(r),raw:e}}}function Re(t){const e=t.trim();if(!e)return{text:t,unwrapped:!1};if(G.test(e)||e.includes(`
`))return{text:t,unwrapped:!1};const a=mt(e);return a?a.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).some(s=>G.test(s))?{text:a.replace(/\r\n/g,`
`),unwrapped:!0}:{text:t,unwrapped:!1}:{text:t,unwrapped:!1}}function oa(t){const{text:e}=Re(t),a=[];for(const n of e.split(/\r?\n/)){const s=n.trim();!s||s.startsWith("#")||s.startsWith("//")||a.push(Ee(s))}return a}function Ke(t){const e=JSON.parse(t.json||"{}");if(!e||typeof e!="object"||Array.isArray(e))throw new Error("vmess JSON must be an object");return`vmess://${vt(JSON.stringify(e))}`}function je(t){let e="";t.protocol==="ss"&&t.method?e=vt(`${t.method}:${t.password}`):t.user&&t.password?e=`${encodeURIComponent(t.user)}:${encodeURIComponent(t.password)}`:t.user?e=encodeURIComponent(t.user):t.password&&(e=encodeURIComponent(t.password));const a=t.server.includes(":")&&!t.server.startsWith("[")?`[${t.server}]`:t.server,n=t.port?`:${t.port}`:"",s=t.path&&t.path!=="/"?t.path.startsWith("/")?t.path:`/${t.path}`:"",r=Ie(t.params,t.extra),i=t.fragment?`#${encodeURIComponent(t.fragment)}`:"",p=e?`${e}@`:"";return`${t.protocol}://${p}${a}${n}${s}${r?`?${r}`:""}${i}`}function We(t){return yt(t)?t.raw:nt(t)?Ke(t):je(t)}function De(t){return t.map(e=>We(e)).join(`
`)}function Fe(t,e){if(yt(t))return`Link ${e+1}: ${t.error}`;if(nt(t))try{const a=JSON.parse(t.json);return`${t.protocol} ${a.ps||a.add||e+1}`}catch{return`vmess ${e+1}`}return[t.protocol,t.server,t.fragment].filter(Boolean).join(" ")||`Link ${e+1}`}function ia(t){try{return{text:De(t),error:null}}catch(e){return{text:"",error:e instanceof Error?e.message:String(e)}}}const He={class:"flex flex-col gap-3"},Je={key:0,class:"text-muted-color m-0"},Me={class:"font-medium block mb-2"},_e={class:"flex items-center justify-between mb-2 mt-3"},qe={class:"font-semibold"},Qe={key:1,class:"text-muted-color text-sm mt-0 mb-3"},Xe={class:"font-semibold block mb-1 mt-3"},Ze={class:"block mb-2 text-muted-color"},Ge=Pt({__name:"SublinkEditor",props:it({readonly:{type:Boolean,default:!1},idPrefix:{default:""}},{links:{default:()=>[]},linksModifiers:{}}),emits:it(["change"],["update:links"]),setup(t,{emit:e}){const a=t,n=St(t,"links"),s=e,{t:r}=Ct(),i=dt({}),p=dt({});function g(){s("change")}function y(c,b){const l=n.value.slice();l[c]=b,n.value=l,g()}function x(c,b){if(a.readonly)return;const l=n.value[c];if(nt(l))try{const o=JSON.parse(b||"{}");if(!o||typeof o!="object"||Array.isArray(o))throw new Error(r("utils.vmessObject"));p.value={...p.value,[c]:""},y(c,{...l,json:b})}catch(o){p.value={...p.value,[c]:o instanceof Error?o.message:String(o)};const u=n.value.slice();u[c]={...l,json:b},n.value=u}}function w(c,b){if(a.readonly)return;const l=n.value[c];R(l)&&y(c,{...l,...b})}function I(c,b,l,o){if(a.readonly)return;const u=n.value[c];if(!R(u))return;const U=u.params.map((A,gt)=>gt===b?{...A,[l]:o}:A);y(c,{...u,params:U})}function N(c){if(a.readonly)return;const b=n.value[c];R(b)&&y(c,{...b,params:[...b.params,{key:"",value:""}]})}function E(c,b){if(a.readonly)return;const l=n.value[c];R(l)&&y(c,{...l,params:l.params.filter((o,u)=>u!==b)})}function W(c,b){if(a.readonly)return;const l=n.value[c];if(R(l)){if(b.trim())try{JSON.parse(b),i.value={...i.value,[c]:""}}catch(o){i.value={...i.value,[c]:o instanceof Error?o.message:String(o)};const u=n.value.slice();u[c]={...l,extra:b},n.value=u;return}else i.value={...i.value,[c]:""};y(c,{...l,extra:b})}}return(c,b)=>(f(),v("div",He,[n.value.length?B("",!0):(f(),v("p",Je,P(d(r)("utils.emptyLinks")),1)),(f(!0),v(V,null,ot(n.value,(l,o)=>(f(),k(d(It),{key:o,legend:d(Fe)(l,o),toggleable:n.value.length>1},{default:$(()=>[l.kind==="error"?(f(),k(d(q),{key:0,severity:"error",closable:!1},{default:$(()=>[Q(P(l.error),1)]),_:2},1024)):l.kind==="vmess"?(f(),v(V,{key:1},[S("label",Me,P(d(r)("utils.vmessJson")),1),h(d(Z),{"model-value":l.json,class:"w-full font-mono text-sm sublink-json","auto-resize":!1,rows:18,spellcheck:"false",readonly:t.readonly,"onUpdate:modelValue":u=>x(o,u)},null,8,["model-value","readonly","onUpdate:modelValue"]),p.value[o]?(f(),k(d(q),{key:0,severity:"error",class:"mt-2",closable:!1},{default:$(()=>[Q(P(p.value[o]),1)]),_:2},1024)):B("",!0)],64)):(f(),v(V,{key:2},[h(C,{label:d(r)("utils.protocol"),"input-id":`${t.idPrefix}proto-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}proto-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.protocol,"onUpdate:modelValue":u=>w(o,{protocol:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),h(C,{label:d(r)("utils.server"),"input-id":`${t.idPrefix}server-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}server-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.server,"onUpdate:modelValue":u=>w(o,{server:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),h(C,{label:d(r)("utils.port"),"input-id":`${t.idPrefix}port-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}port-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.port,"onUpdate:modelValue":u=>w(o,{port:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),h(C,{label:d(r)("utils.user"),"input-id":`${t.idPrefix}user-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}user-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.user,"onUpdate:modelValue":u=>w(o,{user:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),h(C,{label:d(r)("utils.pass"),"input-id":`${t.idPrefix}pass-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}pass-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.password,"onUpdate:modelValue":u=>w(o,{password:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),l.protocol==="ss"||l.method?(f(),k(C,{key:0,label:d(r)("utils.method"),"input-id":`${t.idPrefix}method-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}method-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.method,"onUpdate:modelValue":u=>w(o,{method:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"])):B("",!0),h(C,{label:d(r)("utils.path"),"input-id":`${t.idPrefix}path-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}path-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.path,"onUpdate:modelValue":u=>w(o,{path:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),h(C,{label:d(r)("utils.fragment"),"input-id":`${t.idPrefix}frag-${o}`},{default:$(()=>[h(d(T),{id:`${t.idPrefix}frag-${o}`,class:"w-full",readonly:t.readonly,"model-value":l.fragment,"onUpdate:modelValue":u=>w(o,{fragment:u})},null,8,["id","readonly","model-value","onUpdate:modelValue"])]),_:2},1032,["label","input-id"]),S("div",_e,[S("span",qe,P(d(r)("utils.queryParams")),1),t.readonly?B("",!0):(f(),k(d(lt),{key:0,icon:"pi pi-plus",size:"small",label:d(r)("utils.addQuery"),onClick:u=>N(o)},null,8,["label","onClick"]))]),(f(!0),v(V,null,ot(l.params,(u,U)=>(f(),v("div",{key:U,class:"flex gap-2 mb-2 items-start"},[h(d(T),{class:"w-36 shrink-0",placeholder:d(r)("utils.queryKey"),readonly:t.readonly,"model-value":u.key,"onUpdate:modelValue":A=>I(o,U,"key",A)},null,8,["placeholder","readonly","model-value","onUpdate:modelValue"]),h(d(T),{class:"flex-auto min-w-0",placeholder:d(r)("utils.queryValue"),readonly:t.readonly,"model-value":u.value,"onUpdate:modelValue":A=>I(o,U,"value",A)},null,8,["placeholder","readonly","model-value","onUpdate:modelValue"]),t.readonly?B("",!0):(f(),k(d(lt),{key:0,icon:"pi pi-times",text:"",rounded:"",severity:"danger","aria-label":d(r)("common.delete"),onClick:A=>E(o,U)},null,8,["aria-label","onClick"]))]))),128)),l.params.length?B("",!0):(f(),v("p",Qe,P(d(r)("utils.noQuery")),1)),S("label",Xe,P(d(r)("utils.extraJson")),1),S("small",Ze,P(d(r)("utils.extraHint")),1),h(d(Z),{class:"w-full font-mono text-sm sublink-json","auto-resize":!1,rows:14,spellcheck:"false",placeholder:`{
  
}`,readonly:t.readonly,"model-value":l.extra,"onUpdate:modelValue":u=>W(o,u)},null,8,["readonly","model-value","onUpdate:modelValue"]),i.value[o]?(f(),k(d(q),{key:2,severity:"error",class:"mt-2",closable:!1},{default:$(()=>[Q(P(i.value[o]),1)]),_:2},1024)):B("",!0)],64))]),_:2},1032,["legend","toggleable"]))),128))]))}}),la=Ot(Ge,[["__scopeId","data-v-e5e43cca"]]);export{la as S,qt as a,re as b,de as c,be as d,Z as e,vt as f,at as g,ra as h,sa as i,oa as p,Et as s,ia as t,Re as u};
