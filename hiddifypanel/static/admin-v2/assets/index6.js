import{b as S,a as P}from"./index2.js";import{B as M,R as $,i as L,j as k,V as z,o as u,c as f,e as l,k as g,g as i,f as m,l as y,v,n as F,p as A,q as U,a as T,w as x,x as C,T as R,a7 as c,aa as d,aS as X}from"./index.js";var Y=`
    .p-fieldset {
        background: dt('fieldset.background');
        border: 1px solid dt('fieldset.border.color');
        border-radius: dt('fieldset.border.radius');
        color: dt('fieldset.color');
        padding: dt('fieldset.padding');
        margin: 0;
    }

    .p-fieldset-legend {
        background: dt('fieldset.legend.background');
        border-radius: dt('fieldset.legend.border.radius');
        border-width: dt('fieldset.legend.border.width');
        border-style: solid;
        border-color: dt('fieldset.legend.border.color');
        color: dt('fieldset.legend.color');
        padding: dt('fieldset.legend.padding');
        transition:
            background dt('fieldset.transition.duration'),
            color dt('fieldset.transition.duration'),
            outline-color dt('fieldset.transition.duration'),
            box-shadow dt('fieldset.transition.duration');
    }

    .p-fieldset-toggleable > .p-fieldset-legend {
        padding: 0;
    }

    .p-fieldset-toggle-button {
        cursor: pointer;
        user-select: none;
        overflow: hidden;
        position: relative;
        text-decoration: none;
        display: flex;
        gap: dt('fieldset.legend.gap');
        align-items: center;
        justify-content: center;
        padding: dt('fieldset.legend.padding');
        background: transparent;
        border: 0 none;
        border-radius: dt('fieldset.legend.border.radius');
        transition:
            background dt('fieldset.transition.duration'),
            color dt('fieldset.transition.duration'),
            outline-color dt('fieldset.transition.duration'),
            box-shadow dt('fieldset.transition.duration');
        outline-color: transparent;
    }

    .p-fieldset-legend-label {
        font-weight: dt('fieldset.legend.font.weight');
    }

    .p-fieldset-toggle-button:focus-visible {
        box-shadow: dt('fieldset.legend.focus.ring.shadow');
        outline: dt('fieldset.legend.focus.ring.width') dt('fieldset.legend.focus.ring.style') dt('fieldset.legend.focus.ring.color');
        outline-offset: dt('fieldset.legend.focus.ring.offset');
    }

    .p-fieldset-toggleable > .p-fieldset-legend:hover {
        color: dt('fieldset.legend.hover.color');
        background: dt('fieldset.legend.hover.background');
    }

    .p-fieldset-toggle-icon {
        color: dt('fieldset.toggle.icon.color');
        transition: color dt('fieldset.transition.duration');
    }

    .p-fieldset-toggleable > .p-fieldset-legend:hover .p-fieldset-toggle-icon {
        color: dt('fieldset.toggle.icon.hover.color');
    }

    .p-fieldset-content-container {
        display: grid;
        grid-template-rows: 1fr;
    }

    .p-fieldset-content-wrapper {
        min-height: 0;
    }

    .p-fieldset-content {
        padding: dt('fieldset.content.padding');
    }
`,K={root:function(e){var o=e.props;return["p-fieldset p-component",{"p-fieldset-toggleable":o.toggleable}]},legend:"p-fieldset-legend",legendLabel:"p-fieldset-legend-label",toggleButton:"p-fieldset-toggle-button",toggleIcon:"p-fieldset-toggle-icon",contentContainer:"p-fieldset-content-container",contentWrapper:"p-fieldset-content-wrapper",content:"p-fieldset-content"},I=M.extend({name:"fieldset",style:Y,classes:K}),O={name:"BaseFieldset",extends:L,props:{legend:String,toggleable:Boolean,collapsed:Boolean,toggleButtonProps:{type:null,default:null}},style:I,provide:function(){return{$pcFieldset:this,$parentInstance:this}}},j={name:"Fieldset",extends:O,inheritAttrs:!1,emits:["update:collapsed","toggle"],data:function(){return{d_collapsed:this.collapsed}},watch:{collapsed:function(e){this.d_collapsed=e}},methods:{toggle:function(e){this.d_collapsed=!this.d_collapsed,this.$emit("update:collapsed",this.d_collapsed),this.$emit("toggle",{originalEvent:e,value:this.d_collapsed})},onKeyDown:function(e){(e.code==="Enter"||e.code==="NumpadEnter"||e.code==="Space")&&(this.toggle(e),e.preventDefault())}},computed:{buttonAriaLabel:function(){return this.toggleButtonProps&&this.toggleButtonProps.ariaLabel?this.toggleButtonProps.ariaLabel:this.legend},dataP:function(){return k({toggleable:this.toggleable})}},directives:{ripple:$},components:{PlusIcon:P,MinusIcon:S}};function p(t){"@babel/helpers - typeof";return p=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(e){return typeof e}:function(e){return e&&typeof Symbol=="function"&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},p(t)}function B(t,e){var o=Object.keys(t);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(t);e&&(r=r.filter(function(s){return Object.getOwnPropertyDescriptor(t,s).enumerable})),o.push.apply(o,r)}return o}function w(t){for(var e=1;e<arguments.length;e++){var o=arguments[e]!=null?arguments[e]:{};e%2?B(Object(o),!0).forEach(function(r){E(t,r,o[r])}):Object.getOwnPropertyDescriptors?Object.defineProperties(t,Object.getOwnPropertyDescriptors(o)):B(Object(o)).forEach(function(r){Object.defineProperty(t,r,Object.getOwnPropertyDescriptor(o,r))})}return t}function E(t,e,o){return(e=H(e))in t?Object.defineProperty(t,e,{value:o,enumerable:!0,configurable:!0,writable:!0}):t[e]=o,t}function H(t){var e=N(t,"string");return p(e)=="symbol"?e:e+""}function N(t,e){if(p(t)!="object"||!t)return t;var o=t[Symbol.toPrimitive];if(o!==void 0){var r=o.call(t,e);if(p(r)!="object")return r;throw new TypeError("@@toPrimitive must return a primitive value.")}return(e==="string"?String:Number)(t)}var q=["data-p"],W=["data-p"],V=["id"],G=["id","aria-controls","aria-expanded","aria-label"],J=["id","aria-labelledby"];function Q(t,e,o,r,s,n){var a=z("ripple");return u(),f("fieldset",i({class:t.cx("root"),"data-p":n.dataP},t.ptmi("root")),[l("legend",i({class:t.cx("legend"),"data-p":n.dataP},t.ptm("legend")),[g(t.$slots,"legend",{toggleCallback:n.toggle},function(){return[t.toggleable?y("",!0):(u(),f("span",i({key:0,id:t.$id+"_header",class:t.cx("legendLabel")},t.ptm("legendLabel")),m(t.legend),17,V)),t.toggleable?v((u(),f("button",i({key:1,id:t.$id+"_header",type:"button","aria-controls":t.$id+"_content","aria-expanded":!s.d_collapsed,"aria-label":n.buttonAriaLabel,class:t.cx("toggleButton"),onClick:e[0]||(e[0]=function(){return n.toggle&&n.toggle.apply(n,arguments)}),onKeydown:e[1]||(e[1]=function(){return n.onKeyDown&&n.onKeyDown.apply(n,arguments)})},w(w({},t.toggleButtonProps),t.ptm("toggleButton"))),[g(t.$slots,t.$slots.toggleicon?"toggleicon":"togglericon",{collapsed:s.d_collapsed,class:F(t.cx("toggleIcon"))},function(){return[(u(),A(U(s.d_collapsed?"PlusIcon":"MinusIcon"),i({class:t.cx("toggleIcon")},t.ptm("toggleIcon")),null,16,["class"]))]}),l("span",i({class:t.cx("legendLabel")},t.ptm("legendLabel")),m(t.legend),17)],16,G)),[[a]]):y("",!0)]})],16,W),T(R,i({name:"p-collapsible"},t.ptm("transition")),{default:x(function(){return[v(l("div",i({id:t.$id+"_content",class:t.cx("contentContainer"),role:"region","aria-labelledby":t.$id+"_header"},t.ptm("contentContainer")),[l("div",i({class:t.cx("contentWrapper")},t.ptm("contentWrapper")),[l("div",i({class:t.cx("content")},t.ptm("content")),[g(t.$slots,"default")],16)],16)],16,J),[[C,!s.d_collapsed]])]}),_:3},16)],16,q)}j.render=Q;var Z=`
    .p-scrollpanel-content-container {
        overflow: hidden;
        width: 100%;
        height: 100%;
        position: relative;
        z-index: 1;
        float: left;
    }

    .p-scrollpanel-content {
        height: calc(100% + calc(2 * dt('scrollpanel.bar.size')));
        width: calc(100% + calc(2 * dt('scrollpanel.bar.size')));
        padding-inline: 0 calc(2 * dt('scrollpanel.bar.size'));
        padding-block: 0 calc(2 * dt('scrollpanel.bar.size'));
        position: relative;
        overflow: auto;
        box-sizing: border-box;
        scrollbar-width: none;
    }

    .p-scrollpanel-content::-webkit-scrollbar {
        display: none;
    }

    .p-scrollpanel-bar {
        position: relative;
        border-radius: dt('scrollpanel.bar.border.radius');
        z-index: 2;
        cursor: pointer;
        opacity: 0;
        outline-color: transparent;
        background: dt('scrollpanel.bar.background');
        border: 0 none;
        transition:
            outline-color dt('scrollpanel.transition.duration'),
            opacity dt('scrollpanel.transition.duration');
    }

    .p-scrollpanel-bar:focus-visible {
        box-shadow: dt('scrollpanel.bar.focus.ring.shadow');
        outline: dt('scrollpanel.barfocus.ring.width') dt('scrollpanel.bar.focus.ring.style') dt('scrollpanel.bar.focus.ring.color');
        outline-offset: dt('scrollpanel.barfocus.ring.offset');
    }

    .p-scrollpanel-bar-y {
        width: dt('scrollpanel.bar.size');
        inset-block-start: 0;
    }

    .p-scrollpanel-bar-x {
        height: dt('scrollpanel.bar.size');
        inset-block-end: 0;
    }

    .p-scrollpanel-hidden {
        visibility: hidden;
    }

    .p-scrollpanel:hover .p-scrollpanel-bar,
    .p-scrollpanel:active .p-scrollpanel-bar {
        opacity: 1;
    }

    .p-scrollpanel-grabbed {
        user-select: none;
    }
`,_={root:"p-scrollpanel p-component",contentContainer:"p-scrollpanel-content-container",content:"p-scrollpanel-content",barX:"p-scrollpanel-bar p-scrollpanel-bar-x",barY:"p-scrollpanel-bar p-scrollpanel-bar-y"},ee=M.extend({name:"scrollpanel",style:Z,classes:_}),te={name:"BaseScrollPanel",extends:L,props:{step:{type:Number,default:5}},style:ee,provide:function(){return{$pcScrollPanel:this,$parentInstance:this}}},ne={name:"ScrollPanel",extends:te,inheritAttrs:!1,initialized:!1,documentResizeListener:null,documentMouseMoveListener:null,documentMouseUpListener:null,frame:null,scrollXRatio:null,scrollYRatio:null,isXBarClicked:!1,isYBarClicked:!1,lastPageX:null,lastPageY:null,timer:null,outsideClickListener:null,data:function(){return{orientation:"vertical",lastScrollTop:0,lastScrollLeft:0}},mounted:function(){this.$el.offsetParent&&this.initialize()},updated:function(){!this.initialized&&this.$el.offsetParent&&this.initialize()},beforeUnmount:function(){this.unbindDocumentResizeListener(),this.frame&&window.cancelAnimationFrame(this.frame)},methods:{initialize:function(){this.moveBar(),this.bindDocumentResizeListener(),this.calculateContainerHeight()},calculateContainerHeight:function(){var e=getComputedStyle(this.$el),o=getComputedStyle(this.$refs.xBar),r=X(this.$el)-parseInt(o.height,10);e["max-height"]!=="none"&&r===0&&(this.$refs.content.offsetHeight+parseInt(o.height,10)>parseInt(e["max-height"],10)?this.$el.style.height=e["max-height"]:this.$el.style.height=this.$refs.content.offsetHeight+parseFloat(e.paddingTop)+parseFloat(e.paddingBottom)+parseFloat(e.borderTopWidth)+parseFloat(e.borderBottomWidth)+"px")},moveBar:function(){var e=this;if(this.$refs.content){var o=this.$refs.content.scrollWidth,r=this.$refs.content.clientWidth,s=(this.$el.clientHeight-this.$refs.xBar.clientHeight)*-1;this.scrollXRatio=r/o;var n=this.$refs.content.scrollHeight,a=this.$refs.content.clientHeight,D=(this.$el.clientWidth-this.$refs.yBar.clientWidth)*-1;this.scrollYRatio=a/n;var h=Math.max(this.scrollXRatio*100,10),b=Math.max(this.scrollYRatio*100,10);this.frame=this.requestAnimationFrame(function(){e.$refs.xBar&&(e.scrollXRatio>=1?(e.$refs.xBar.setAttribute("data-p-scrollpanel-hidden","true"),!e.isUnstyled&&d(e.$refs.xBar,"p-scrollpanel-hidden")):(e.$refs.xBar.setAttribute("data-p-scrollpanel-hidden","false"),!e.isUnstyled&&c(e.$refs.xBar,"p-scrollpanel-hidden"),e.$refs.xBar.style.cssText="width:"+h+"%; inset-inline-start:"+Math.abs(e.$refs.content.scrollLeft)/(o-r)*(100-h)+"%;bottom:"+s+"px;")),e.$refs.yBar&&(e.scrollYRatio>=1?(e.$refs.yBar.setAttribute("data-p-scrollpanel-hidden","true"),!e.isUnstyled&&d(e.$refs.yBar,"p-scrollpanel-hidden")):(e.$refs.yBar.setAttribute("data-p-scrollpanel-hidden","false"),!e.isUnstyled&&c(e.$refs.yBar,"p-scrollpanel-hidden"),e.$refs.yBar.style.cssText="height:"+b+"%; top: calc("+e.$refs.content.scrollTop/(n-a)*(100-b)+"% - "+e.$refs.xBar.clientHeight+"px); inset-inline-end:"+D+"px;"))})}},onYBarMouseDown:function(e){this.isYBarClicked=!0,this.$refs.yBar.focus(),this.lastPageY=e.pageY,this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","true"),!this.isUnstyled&&d(this.$refs.yBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","true"),!this.isUnstyled&&d(document.body,"p-scrollpanel-grabbed"),this.bindDocumentMouseListeners(),e.preventDefault()},onXBarMouseDown:function(e){this.isXBarClicked=!0,this.$refs.xBar.focus(),this.lastPageX=e.pageX,this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&d(this.$refs.xBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&d(document.body,"p-scrollpanel-grabbed"),this.bindDocumentMouseListeners(),e.preventDefault()},onScroll:function(e){this.lastScrollLeft!==e.target.scrollLeft?(this.lastScrollLeft=e.target.scrollLeft,this.orientation="horizontal"):this.lastScrollTop!==e.target.scrollTop&&(this.lastScrollTop=e.target.scrollTop,this.orientation="vertical"),this.moveBar()},onKeyDown:function(e){if(this.orientation==="vertical")switch(e.code){case"ArrowDown":{this.setTimer("scrollTop",this.step),e.preventDefault();break}case"ArrowUp":{this.setTimer("scrollTop",this.step*-1),e.preventDefault();break}case"ArrowLeft":case"ArrowRight":{e.preventDefault();break}}else if(this.orientation==="horizontal")switch(e.code){case"ArrowRight":{this.setTimer("scrollLeft",this.step),e.preventDefault();break}case"ArrowLeft":{this.setTimer("scrollLeft",this.step*-1),e.preventDefault();break}case"ArrowDown":case"ArrowUp":{e.preventDefault();break}}},onKeyUp:function(){this.clearTimer()},repeat:function(e,o){this.$refs.content[e]+=o,this.moveBar()},setTimer:function(e,o){var r=this;this.clearTimer(),this.timer=setTimeout(function(){r.repeat(e,o)},40)},clearTimer:function(){this.timer&&clearTimeout(this.timer)},onDocumentMouseMove:function(e){this.isXBarClicked?this.onMouseMoveForXBar(e):this.isYBarClicked?this.onMouseMoveForYBar(e):(this.onMouseMoveForXBar(e),this.onMouseMoveForYBar(e))},onMouseMoveForXBar:function(e){var o=this,r=e.pageX-this.lastPageX;this.lastPageX=e.pageX,this.frame=this.requestAnimationFrame(function(){o.$refs.content.scrollLeft+=r/o.scrollXRatio})},onMouseMoveForYBar:function(e){var o=this,r=e.pageY-this.lastPageY;this.lastPageY=e.pageY,this.frame=this.requestAnimationFrame(function(){o.$refs.content.scrollTop+=r/o.scrollYRatio})},onFocus:function(e){this.$refs.xBar.isSameNode(e.target)?this.orientation="horizontal":this.$refs.yBar.isSameNode(e.target)&&(this.orientation="vertical")},onBlur:function(){this.orientation==="horizontal"&&(this.orientation="vertical")},onDocumentMouseUp:function(){this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(this.$refs.yBar,"p-scrollpanel-grabbed"),this.$refs.xBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(this.$refs.xBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(document.body,"p-scrollpanel-grabbed"),this.unbindDocumentMouseListeners(),this.isXBarClicked=!1,this.isYBarClicked=!1},requestAnimationFrame:function(e){var o=window.requestAnimationFrame||this.timeoutFrame;return o(e)},refresh:function(){this.moveBar()},scrollTop:function(e){var o=this.$refs.content.scrollHeight-this.$refs.content.clientHeight;e=e>o?o:e>0?e:0,this.$refs.content.scrollTop=e},timeoutFrame:function(e){setTimeout(e,0)},bindDocumentMouseListeners:function(){var e=this;this.documentMouseMoveListener||(this.documentMouseMoveListener=function(o){e.onDocumentMouseMove(o)},document.addEventListener("mousemove",this.documentMouseMoveListener)),this.documentMouseUpListener||(this.documentMouseUpListener=function(o){e.onDocumentMouseUp(o)},document.addEventListener("mouseup",this.documentMouseUpListener))},unbindDocumentMouseListeners:function(){this.documentMouseMoveListener&&(document.removeEventListener("mousemove",this.documentMouseMoveListener),this.documentMouseMoveListener=null),this.documentMouseUpListener&&(document.removeEventListener("mouseup",this.documentMouseUpListener),this.documentMouseUpListener=null)},bindDocumentResizeListener:function(){var e=this;this.documentResizeListener||(this.documentResizeListener=function(){e.moveBar()},window.addEventListener("resize",this.documentResizeListener))},unbindDocumentResizeListener:function(){this.documentResizeListener&&(window.removeEventListener("resize",this.documentResizeListener),this.documentResizeListener=null)}},computed:{contentId:function(){return this.$id+"_content"}}},oe=["id"],re=["aria-controls","aria-valuenow"],ie=["aria-controls","aria-valuenow"];function se(t,e,o,r,s,n){return u(),f("div",i({class:t.cx("root")},t.ptmi("root")),[l("div",i({class:t.cx("contentContainer")},t.ptm("contentContainer")),[l("div",i({ref:"content",id:n.contentId,class:t.cx("content"),onScroll:e[0]||(e[0]=function(){return n.onScroll&&n.onScroll.apply(n,arguments)}),onMouseenter:e[1]||(e[1]=function(){return n.moveBar&&n.moveBar.apply(n,arguments)})},t.ptm("content")),[g(t.$slots,"default")],16,oe)],16),l("div",i({ref:"xBar",class:t.cx("barx"),tabindex:"0",role:"scrollbar","aria-orientation":"horizontal","aria-controls":n.contentId,"aria-valuenow":s.lastScrollLeft,onMousedown:e[2]||(e[2]=function(){return n.onXBarMouseDown&&n.onXBarMouseDown.apply(n,arguments)}),onKeydown:e[3]||(e[3]=function(a){return n.onKeyDown(a)}),onKeyup:e[4]||(e[4]=function(){return n.onKeyUp&&n.onKeyUp.apply(n,arguments)}),onFocus:e[5]||(e[5]=function(){return n.onFocus&&n.onFocus.apply(n,arguments)}),onBlur:e[6]||(e[6]=function(){return n.onBlur&&n.onBlur.apply(n,arguments)})},t.ptm("barx"),{"data-pc-group-section":"bar"}),null,16,re),l("div",i({ref:"yBar",class:t.cx("bary"),tabindex:"0",role:"scrollbar","aria-orientation":"vertical","aria-controls":n.contentId,"aria-valuenow":s.lastScrollTop,onMousedown:e[7]||(e[7]=function(){return n.onYBarMouseDown&&n.onYBarMouseDown.apply(n,arguments)}),onKeydown:e[8]||(e[8]=function(a){return n.onKeyDown(a)}),onKeyup:e[9]||(e[9]=function(){return n.onKeyUp&&n.onKeyUp.apply(n,arguments)}),onFocus:e[10]||(e[10]=function(){return n.onFocus&&n.onFocus.apply(n,arguments)})},t.ptm("bary"),{"data-pc-group-section":"bar"}),null,16,ie)],16)}ne.render=se;export{ne as a,j as s};
