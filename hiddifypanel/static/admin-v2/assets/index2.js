import{s as m,o as p,c,e as s,g as o,B as $,R as A,h as B,i as k,j as S,r as I,k as d,f as P,l as g,n as T,a as b,w as y,p as D,q as H,v as j,x as L,T as M}from"./index.js";var v={name:"MinusIcon",extends:m};function V(e){return N(e)||W(e)||K(e)||E()}function E(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function K(e,n){if(e){if(typeof e=="string")return f(e,n);var t={}.toString.call(e).slice(8,-1);return t==="Object"&&e.constructor&&(t=e.constructor.name),t==="Map"||t==="Set"?Array.from(e):t==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t)?f(e,n):void 0}}function W(e){if(typeof Symbol<"u"&&e[Symbol.iterator]!=null||e["@@iterator"]!=null)return Array.from(e)}function N(e){if(Array.isArray(e))return f(e)}function f(e,n){(n==null||n>e.length)&&(n=e.length);for(var t=0,a=Array(n);t<n;t++)a[t]=e[t];return a}function O(e,n,t,a,l,r){return p(),c("svg",o({width:"14",height:"14",viewBox:"0 0 14 14",fill:"none",xmlns:"http://www.w3.org/2000/svg"},e.pti()),V(n[0]||(n[0]=[s("path",{d:"M13.2222 7.77778H0.777778C0.571498 7.77778 0.373667 7.69584 0.227806 7.54998C0.0819442 7.40412 0 7.20629 0 7.00001C0 6.79373 0.0819442 6.5959 0.227806 6.45003C0.373667 6.30417 0.571498 6.22223 0.777778 6.22223H13.2222C13.4285 6.22223 13.6263 6.30417 13.7722 6.45003C13.9181 6.5959 14 6.79373 14 7.00001C14 7.20629 13.9181 7.40412 13.7722 7.54998C13.6263 7.69584 13.4285 7.77778 13.2222 7.77778Z",fill:"currentColor"},null,-1)])),16)}v.render=O;var C={name:"PlusIcon",extends:m};function R(e){return z(e)||q(e)||Z(e)||U()}function U(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Z(e,n){if(e){if(typeof e=="string")return h(e,n);var t={}.toString.call(e).slice(8,-1);return t==="Object"&&e.constructor&&(t=e.constructor.name),t==="Map"||t==="Set"?Array.from(e):t==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t)?h(e,n):void 0}}function q(e){if(typeof Symbol<"u"&&e[Symbol.iterator]!=null||e["@@iterator"]!=null)return Array.from(e)}function z(e){if(Array.isArray(e))return h(e)}function h(e,n){(n==null||n>e.length)&&(n=e.length);for(var t=0,a=Array(n);t<n;t++)a[t]=e[t];return a}function F(e,n,t,a,l,r){return p(),c("svg",o({width:"14",height:"14",viewBox:"0 0 14 14",fill:"none",xmlns:"http://www.w3.org/2000/svg"},e.pti()),R(n[0]||(n[0]=[s("path",{d:"M7.67742 6.32258V0.677419C7.67742 0.497757 7.60605 0.325452 7.47901 0.198411C7.35197 0.0713707 7.17966 0 7 0C6.82034 0 6.64803 0.0713707 6.52099 0.198411C6.39395 0.325452 6.32258 0.497757 6.32258 0.677419V6.32258H0.677419C0.497757 6.32258 0.325452 6.39395 0.198411 6.52099C0.0713707 6.64803 0 6.82034 0 7C0 7.17966 0.0713707 7.35197 0.198411 7.47901C0.325452 7.60605 0.497757 7.67742 0.677419 7.67742H6.32258V13.3226C6.32492 13.5015 6.39704 13.6725 6.52358 13.799C6.65012 13.9255 6.82106 13.9977 7 14C7.17966 14 7.35197 13.9286 7.47901 13.8016C7.60605 13.6745 7.67742 13.5022 7.67742 13.3226V7.67742H13.3226C13.5022 7.67742 13.6745 7.60605 13.8016 7.47901C13.9286 7.35197 14 7.17966 14 7C13.9977 6.82106 13.9255 6.65012 13.799 6.52358C13.6725 6.39704 13.5015 6.32492 13.3226 6.32258H7.67742Z",fill:"currentColor"},null,-1)])),16)}C.render=F;var G=`
    .p-panel {
        display: block;
        border: 1px solid dt('panel.border.color');
        border-radius: dt('panel.border.radius');
        background: dt('panel.background');
        color: dt('panel.color');
    }

    .p-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: dt('panel.header.padding');
        background: dt('panel.header.background');
        color: dt('panel.header.color');
        border-style: solid;
        border-width: dt('panel.header.border.width');
        border-color: dt('panel.header.border.color');
        border-radius: dt('panel.header.border.radius');
    }

    .p-panel-toggleable .p-panel-header {
        padding: dt('panel.toggleable.header.padding');
    }

    .p-panel-title {
        line-height: 1;
        font-weight: dt('panel.title.font.weight');
    }

    .p-panel-content-container {
        display: grid;
        grid-template-rows: 1fr;
    }

    .p-panel-content-wrapper {
        min-height: 0;
    }

    .p-panel-content {
        padding: dt('panel.content.padding');
    }

    .p-panel-footer {
        padding: dt('panel.footer.padding');
    }
`,J={root:function(n){var t=n.props;return["p-panel p-component",{"p-panel-toggleable":t.toggleable}]},header:"p-panel-header",title:"p-panel-title",headerActions:"p-panel-header-actions",pcToggleButton:"p-panel-toggle-button",contentContainer:"p-panel-content-container",contentWrapper:"p-panel-content-wrapper",content:"p-panel-content",footer:"p-panel-footer"},Q=$.extend({name:"panel",style:G,classes:J}),X={name:"BasePanel",extends:k,props:{header:String,toggleable:Boolean,collapsed:Boolean,toggleButtonProps:{type:Object,default:function(){return{severity:"secondary",text:!0,rounded:!0}}}},style:Q,provide:function(){return{$pcPanel:this,$parentInstance:this}}},Y={name:"Panel",extends:X,inheritAttrs:!1,emits:["update:collapsed","toggle"],data:function(){return{d_collapsed:this.collapsed}},watch:{collapsed:function(n){this.d_collapsed=n}},methods:{toggle:function(n){this.d_collapsed=!this.d_collapsed,this.$emit("update:collapsed",this.d_collapsed),this.$emit("toggle",{originalEvent:n,value:this.d_collapsed})},onKeyDown:function(n){(n.code==="Enter"||n.code==="NumpadEnter"||n.code==="Space")&&(this.toggle(n),n.preventDefault())}},computed:{buttonAriaLabel:function(){return this.toggleButtonProps&&this.toggleButtonProps.ariaLabel?this.toggleButtonProps.ariaLabel:this.header},dataP:function(){return S({toggleable:this.toggleable})}},components:{PlusIcon:C,MinusIcon:v,Button:B},directives:{ripple:A}},_=["data-p"],x=["data-p"],ee=["id"],ne=["id","aria-labelledby"];function te(e,n,t,a,l,r){var w=I("Button");return p(),c("div",o({class:e.cx("root"),"data-p":r.dataP},e.ptmi("root")),[s("div",o({class:e.cx("header"),"data-p":r.dataP},e.ptm("header")),[d(e.$slots,"header",{id:e.$id+"_header",class:T(e.cx("title")),collapsed:l.d_collapsed},function(){return[e.header?(p(),c("span",o({key:0,id:e.$id+"_header",class:e.cx("title")},e.ptm("title")),P(e.header),17,ee)):g("",!0)]}),s("div",o({class:e.cx("headerActions")},e.ptm("headerActions")),[d(e.$slots,"icons"),e.toggleable?d(e.$slots,"togglebutton",{key:0,collapsed:l.d_collapsed,toggleCallback:function(u){return r.toggle(u)},keydownCallback:function(u){return r.onKeyDown(u)}},function(){return[b(w,o({id:e.$id+"_header",class:e.cx("pcToggleButton"),"aria-label":r.buttonAriaLabel,"aria-controls":e.$id+"_content","aria-expanded":!l.d_collapsed,unstyled:e.unstyled,onClick:n[0]||(n[0]=function(i){return r.toggle(i)}),onKeydown:n[1]||(n[1]=function(i){return r.onKeyDown(i)})},e.toggleButtonProps,{pt:e.ptm("pcToggleButton")}),{icon:y(function(i){return[d(e.$slots,e.$slots.toggleicon?"toggleicon":"togglericon",{collapsed:l.d_collapsed},function(){return[(p(),D(H(l.d_collapsed?"PlusIcon":"MinusIcon"),o({class:i.class},e.ptm("pcToggleButton").icon),null,16,["class"]))]})]}),_:3},16,["id","class","aria-label","aria-controls","aria-expanded","unstyled","pt"])]}):g("",!0)],16)],16,x),b(M,o({name:"p-collapsible"},e.ptm("transition")),{default:y(function(){return[j(s("div",o({id:e.$id+"_content",class:e.cx("contentContainer"),role:"region","aria-labelledby":e.$id+"_header"},e.ptm("contentContainer")),[s("div",o({class:e.cx("contentWrapper")},e.ptm("contentWrapper")),[s("div",o({class:e.cx("content")},e.ptm("content")),[d(e.$slots,"default")],16),e.$slots.footer?(p(),c("div",o({key:0,class:e.cx("footer")},e.ptm("footer")),[d(e.$slots,"footer")],16)):g("",!0)],16)],16,ne),[[L,!l.d_collapsed]])]}),_:3},16)],16,_)}Y.render=te;export{C as a,v as b,Y as s};
