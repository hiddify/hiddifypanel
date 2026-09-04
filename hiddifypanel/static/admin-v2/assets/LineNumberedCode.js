import{B as g,i as v,a7 as c,aa as a,aX as y,o as d,c as p,e as i,g as u,k as B,d as M,F as L,D as w,G as D,n as x,f as m,_ as z}from"./index.js";var F=`
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
`,U={root:"p-scrollpanel p-component",contentContainer:"p-scrollpanel-content-container",content:"p-scrollpanel-content",barX:"p-scrollpanel-bar p-scrollpanel-bar-x",barY:"p-scrollpanel-bar p-scrollpanel-bar-y"},$=g.extend({name:"scrollpanel",style:F,classes:U}),A={name:"BaseScrollPanel",extends:v,props:{step:{type:Number,default:5}},style:$,provide:function(){return{$pcScrollPanel:this,$parentInstance:this}}},S={name:"ScrollPanel",extends:A,inheritAttrs:!1,initialized:!1,documentResizeListener:null,documentMouseMoveListener:null,documentMouseUpListener:null,frame:null,scrollXRatio:null,scrollYRatio:null,isXBarClicked:!1,isYBarClicked:!1,lastPageX:null,lastPageY:null,timer:null,outsideClickListener:null,data:function(){return{orientation:"vertical",lastScrollTop:0,lastScrollLeft:0}},mounted:function(){this.$el.offsetParent&&this.initialize()},updated:function(){!this.initialized&&this.$el.offsetParent&&this.initialize()},beforeUnmount:function(){this.unbindDocumentResizeListener(),this.frame&&window.cancelAnimationFrame(this.frame)},methods:{initialize:function(){this.moveBar(),this.bindDocumentResizeListener(),this.calculateContainerHeight()},calculateContainerHeight:function(){var e=getComputedStyle(this.$el),r=getComputedStyle(this.$refs.xBar),s=y(this.$el)-parseInt(r.height,10);e["max-height"]!=="none"&&s===0&&(this.$refs.content.offsetHeight+parseInt(r.height,10)>parseInt(e["max-height"],10)?this.$el.style.height=e["max-height"]:this.$el.style.height=this.$refs.content.offsetHeight+parseFloat(e.paddingTop)+parseFloat(e.paddingBottom)+parseFloat(e.borderTopWidth)+parseFloat(e.borderBottomWidth)+"px")},moveBar:function(){var e=this;if(this.$refs.content){var r=this.$refs.content.scrollWidth,s=this.$refs.content.clientWidth,l=(this.$el.clientHeight-this.$refs.xBar.clientHeight)*-1;this.scrollXRatio=s/r;var n=this.$refs.content.scrollHeight,o=this.$refs.content.clientHeight,b=(this.$el.clientWidth-this.$refs.yBar.clientWidth)*-1;this.scrollYRatio=o/n;var h=Math.max(this.scrollXRatio*100,10),f=Math.max(this.scrollYRatio*100,10);this.frame=this.requestAnimationFrame(function(){e.$refs.xBar&&(e.scrollXRatio>=1?(e.$refs.xBar.setAttribute("data-p-scrollpanel-hidden","true"),!e.isUnstyled&&a(e.$refs.xBar,"p-scrollpanel-hidden")):(e.$refs.xBar.setAttribute("data-p-scrollpanel-hidden","false"),!e.isUnstyled&&c(e.$refs.xBar,"p-scrollpanel-hidden"),e.$refs.xBar.style.cssText="width:"+h+"%; inset-inline-start:"+Math.abs(e.$refs.content.scrollLeft)/(r-s)*(100-h)+"%;bottom:"+l+"px;")),e.$refs.yBar&&(e.scrollYRatio>=1?(e.$refs.yBar.setAttribute("data-p-scrollpanel-hidden","true"),!e.isUnstyled&&a(e.$refs.yBar,"p-scrollpanel-hidden")):(e.$refs.yBar.setAttribute("data-p-scrollpanel-hidden","false"),!e.isUnstyled&&c(e.$refs.yBar,"p-scrollpanel-hidden"),e.$refs.yBar.style.cssText="height:"+f+"%; top: calc("+e.$refs.content.scrollTop/(n-o)*(100-f)+"% - "+e.$refs.xBar.clientHeight+"px); inset-inline-end:"+b+"px;"))})}},onYBarMouseDown:function(e){this.isYBarClicked=!0,this.$refs.yBar.focus(),this.lastPageY=e.pageY,this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","true"),!this.isUnstyled&&a(this.$refs.yBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","true"),!this.isUnstyled&&a(document.body,"p-scrollpanel-grabbed"),this.bindDocumentMouseListeners(),e.preventDefault()},onXBarMouseDown:function(e){this.isXBarClicked=!0,this.$refs.xBar.focus(),this.lastPageX=e.pageX,this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&a(this.$refs.xBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&a(document.body,"p-scrollpanel-grabbed"),this.bindDocumentMouseListeners(),e.preventDefault()},onScroll:function(e){this.lastScrollLeft!==e.target.scrollLeft?(this.lastScrollLeft=e.target.scrollLeft,this.orientation="horizontal"):this.lastScrollTop!==e.target.scrollTop&&(this.lastScrollTop=e.target.scrollTop,this.orientation="vertical"),this.moveBar()},onKeyDown:function(e){if(this.orientation==="vertical")switch(e.code){case"ArrowDown":{this.setTimer("scrollTop",this.step),e.preventDefault();break}case"ArrowUp":{this.setTimer("scrollTop",this.step*-1),e.preventDefault();break}case"ArrowLeft":case"ArrowRight":{e.preventDefault();break}}else if(this.orientation==="horizontal")switch(e.code){case"ArrowRight":{this.setTimer("scrollLeft",this.step),e.preventDefault();break}case"ArrowLeft":{this.setTimer("scrollLeft",this.step*-1),e.preventDefault();break}case"ArrowDown":case"ArrowUp":{e.preventDefault();break}}},onKeyUp:function(){this.clearTimer()},repeat:function(e,r){this.$refs.content[e]+=r,this.moveBar()},setTimer:function(e,r){var s=this;this.clearTimer(),this.timer=setTimeout(function(){s.repeat(e,r)},40)},clearTimer:function(){this.timer&&clearTimeout(this.timer)},onDocumentMouseMove:function(e){this.isXBarClicked?this.onMouseMoveForXBar(e):this.isYBarClicked?this.onMouseMoveForYBar(e):(this.onMouseMoveForXBar(e),this.onMouseMoveForYBar(e))},onMouseMoveForXBar:function(e){var r=this,s=e.pageX-this.lastPageX;this.lastPageX=e.pageX,this.frame=this.requestAnimationFrame(function(){r.$refs.content.scrollLeft+=s/r.scrollXRatio})},onMouseMoveForYBar:function(e){var r=this,s=e.pageY-this.lastPageY;this.lastPageY=e.pageY,this.frame=this.requestAnimationFrame(function(){r.$refs.content.scrollTop+=s/r.scrollYRatio})},onFocus:function(e){this.$refs.xBar.isSameNode(e.target)?this.orientation="horizontal":this.$refs.yBar.isSameNode(e.target)&&(this.orientation="vertical")},onBlur:function(){this.orientation==="horizontal"&&(this.orientation="vertical")},onDocumentMouseUp:function(){this.$refs.yBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(this.$refs.yBar,"p-scrollpanel-grabbed"),this.$refs.xBar.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(this.$refs.xBar,"p-scrollpanel-grabbed"),document.body.setAttribute("data-p-scrollpanel-grabbed","false"),!this.isUnstyled&&c(document.body,"p-scrollpanel-grabbed"),this.unbindDocumentMouseListeners(),this.isXBarClicked=!1,this.isYBarClicked=!1},requestAnimationFrame:function(e){var r=window.requestAnimationFrame||this.timeoutFrame;return r(e)},refresh:function(){this.moveBar()},scrollTop:function(e){var r=this.$refs.content.scrollHeight-this.$refs.content.clientHeight;e=e>r?r:e>0?e:0,this.$refs.content.scrollTop=e},timeoutFrame:function(e){setTimeout(e,0)},bindDocumentMouseListeners:function(){var e=this;this.documentMouseMoveListener||(this.documentMouseMoveListener=function(r){e.onDocumentMouseMove(r)},document.addEventListener("mousemove",this.documentMouseMoveListener)),this.documentMouseUpListener||(this.documentMouseUpListener=function(r){e.onDocumentMouseUp(r)},document.addEventListener("mouseup",this.documentMouseUpListener))},unbindDocumentMouseListeners:function(){this.documentMouseMoveListener&&(document.removeEventListener("mousemove",this.documentMouseMoveListener),this.documentMouseMoveListener=null),this.documentMouseUpListener&&(document.removeEventListener("mouseup",this.documentMouseUpListener),this.documentMouseUpListener=null)},bindDocumentResizeListener:function(){var e=this;this.documentResizeListener||(this.documentResizeListener=function(){e.moveBar()},window.addEventListener("resize",this.documentResizeListener))},unbindDocumentResizeListener:function(){this.documentResizeListener&&(window.removeEventListener("resize",this.documentResizeListener),this.documentResizeListener=null)}},computed:{contentId:function(){return this.$id+"_content"}}},T=["id"],X=["aria-controls","aria-valuenow"],Y=["aria-controls","aria-valuenow"];function k(t,e,r,s,l,n){return d(),p("div",u({class:t.cx("root")},t.ptmi("root")),[i("div",u({class:t.cx("contentContainer")},t.ptm("contentContainer")),[i("div",u({ref:"content",id:n.contentId,class:t.cx("content"),onScroll:e[0]||(e[0]=function(){return n.onScroll&&n.onScroll.apply(n,arguments)}),onMouseenter:e[1]||(e[1]=function(){return n.moveBar&&n.moveBar.apply(n,arguments)})},t.ptm("content")),[B(t.$slots,"default")],16,T)],16),i("div",u({ref:"xBar",class:t.cx("barx"),tabindex:"0",role:"scrollbar","aria-orientation":"horizontal","aria-controls":n.contentId,"aria-valuenow":l.lastScrollLeft,onMousedown:e[2]||(e[2]=function(){return n.onXBarMouseDown&&n.onXBarMouseDown.apply(n,arguments)}),onKeydown:e[3]||(e[3]=function(o){return n.onKeyDown(o)}),onKeyup:e[4]||(e[4]=function(){return n.onKeyUp&&n.onKeyUp.apply(n,arguments)}),onFocus:e[5]||(e[5]=function(){return n.onFocus&&n.onFocus.apply(n,arguments)}),onBlur:e[6]||(e[6]=function(){return n.onBlur&&n.onBlur.apply(n,arguments)})},t.ptm("barx"),{"data-pc-group-section":"bar"}),null,16,X),i("div",u({ref:"yBar",class:t.cx("bary"),tabindex:"0",role:"scrollbar","aria-orientation":"vertical","aria-controls":n.contentId,"aria-valuenow":l.lastScrollTop,onMousedown:e[7]||(e[7]=function(){return n.onYBarMouseDown&&n.onYBarMouseDown.apply(n,arguments)}),onKeydown:e[8]||(e[8]=function(o){return n.onKeyDown(o)}),onKeyup:e[9]||(e[9]=function(){return n.onKeyUp&&n.onKeyUp.apply(n,arguments)}),onFocus:e[10]||(e[10]=function(){return n.onFocus&&n.onFocus.apply(n,arguments)})},t.ptm("bary"),{"data-pc-group-section":"bar"}),null,16,Y)],16)}S.render=k;const R={class:"line-numbered-code"},C={class:"line-numbered-code__table"},P={class:"line-numbered-code__gutter"},K={class:"line-numbered-code__line"},H=M({__name:"LineNumberedCode",props:{text:{},highlightLine:{}},setup(t){const e=t,r=D(()=>e.text.split(`
`));return(s,l)=>(d(),p("div",R,[i("table",C,[i("tbody",null,[(d(!0),p(L,null,w(r.value,(n,o)=>(d(),p("tr",{key:o,class:x({"line-numbered-code__row--highlight":t.highlightLine===o+1})},[i("td",P,m(o+1),1),i("td",K,[i("code",null,m(n||" "),1)])],2))),128))])])]))}}),E=z(H,[["__scopeId","data-v-099b3cfc"]]);export{E as L,S as s};
