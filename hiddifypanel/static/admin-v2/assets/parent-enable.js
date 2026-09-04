import{B as re,aL as he,i as fe,j as $,o as r,c as u,k as b,g as o,p as v,q as T,l as m,f as g,$ as me,Z as be,L as ge,a1 as ye,R as ve,P as D,O as Oe,ao as Ie,aj as Se,aM as q,Y as W,aN as ke,au as we,aO as Le,a4 as xe,aw as Ce,av as Q,ag as Fe,ai as E,aP as Ve,at as Te,aQ as Ke,a5 as R,r as C,V as Me,e as w,F as A,C as K,D as _,a as x,w as S,n as F,T as De,X as Ee,W as Ae,v as Pe,d as Re,aR as ze,u as oe,y as $e,b as P,A as ee,z as Be,aS as He,E as je,G as J,_ as Ge,I as Ne}from"./index.js";import{f as Ue,i as qe,b as We,a as Je,e as Ye,g as Qe,C as Xe,O as Ze,s as _e}from"./index5.js";import{s as et,a as tt}from"./index6.js";import{u as it}from"./core-template.js";import{s as nt,L as lt}from"./LineNumberedCode.js";var st=`
    .p-chip {
        display: inline-flex;
        align-items: center;
        background: dt('chip.background');
        color: dt('chip.color');
        border-radius: dt('chip.border.radius');
        padding-block: dt('chip.padding.y');
        padding-inline: dt('chip.padding.x');
        gap: dt('chip.gap');
    }

    .p-chip-icon {
        color: dt('chip.icon.color');
        font-size: dt('chip.icon.size');
        width: dt('chip.icon.size');
        height: dt('chip.icon.size');
    }

    .p-chip-image {
        border-radius: 50%;
        width: dt('chip.image.width');
        height: dt('chip.image.height');
        margin-inline-start: calc(-1 * dt('chip.padding.y'));
    }

    .p-chip:has(.p-chip-remove-icon) {
        padding-inline-end: dt('chip.padding.y');
    }

    .p-chip:has(.p-chip-image) {
        padding-block-start: calc(dt('chip.padding.y') / 2);
        padding-block-end: calc(dt('chip.padding.y') / 2);
    }

    .p-chip-remove-icon {
        cursor: pointer;
        font-size: dt('chip.remove.icon.size');
        width: dt('chip.remove.icon.size');
        height: dt('chip.remove.icon.size');
        color: dt('chip.remove.icon.color');
        border-radius: 50%;
        transition:
            outline-color dt('chip.transition.duration'),
            box-shadow dt('chip.transition.duration');
        outline-color: transparent;
    }

    .p-chip-remove-icon:focus-visible {
        box-shadow: dt('chip.remove.icon.focus.ring.shadow');
        outline: dt('chip.remove.icon.focus.ring.width') dt('chip.remove.icon.focus.ring.style') dt('chip.remove.icon.focus.ring.color');
        outline-offset: dt('chip.remove.icon.focus.ring.offset');
    }
`,rt={root:"p-chip p-component",image:"p-chip-image",icon:"p-chip-icon",label:"p-chip-label",removeIcon:"p-chip-remove-icon"},ot=re.extend({name:"chip",style:st,classes:rt}),at={name:"BaseChip",extends:fe,props:{label:{type:[String,Number],default:null},icon:{type:String,default:null},image:{type:String,default:null},removable:{type:Boolean,default:!1},removeIcon:{type:String,default:void 0}},style:ot,provide:function(){return{$pcChip:this,$parentInstance:this}}},ae={name:"Chip",extends:at,inheritAttrs:!1,emits:["remove"],data:function(){return{visible:!0}},methods:{onKeydown:function(t){(t.key==="Enter"||t.key==="Backspace")&&this.close(t)},close:function(t){this.visible=!1,this.$emit("remove",t)}},computed:{dataP:function(){return $({removable:this.removable})}},components:{TimesCircleIcon:he}},dt=["aria-label","data-p"],ut=["src"];function ct(e,t,i,n,s,l){return s.visible?(r(),u("div",o({key:0,class:e.cx("root"),"aria-label":e.label},e.ptmi("root"),{"data-p":l.dataP}),[b(e.$slots,"default",{},function(){return[e.image?(r(),u("img",o({key:0,src:e.image},e.ptm("image"),{class:e.cx("image")}),null,16,ut)):e.$slots.icon?(r(),v(T(e.$slots.icon),o({key:1,class:e.cx("icon")},e.ptm("icon")),null,16,["class"])):e.icon?(r(),u("span",o({key:2,class:[e.cx("icon"),e.icon]},e.ptm("icon")),null,16)):m("",!0),e.label!==null?(r(),u("div",o({key:3,class:e.cx("label")},e.ptm("label")),g(e.label),17)):m("",!0)]}),e.removable?b(e.$slots,"removeicon",{key:0,removeCallback:l.close,keydownCallback:l.onKeydown},function(){return[(r(),v(T(e.removeIcon?"span":"TimesCircleIcon"),o({class:[e.cx("removeIcon"),e.removeIcon],onClick:l.close,onKeydown:l.onKeydown},e.ptm("removeIcon")),null,16,["class","onClick","onKeydown"]))]}):m("",!0)],16,dt)):m("",!0)}ae.render=ct;var pt=`
    .p-multiselect {
        display: inline-flex;
        cursor: pointer;
        position: relative;
        user-select: none;
        background: dt('multiselect.background');
        border: 1px solid dt('multiselect.border.color');
        transition:
            background dt('multiselect.transition.duration'),
            color dt('multiselect.transition.duration'),
            border-color dt('multiselect.transition.duration'),
            outline-color dt('multiselect.transition.duration'),
            box-shadow dt('multiselect.transition.duration');
        border-radius: dt('multiselect.border.radius');
        outline-color: transparent;
        box-shadow: dt('multiselect.shadow');
    }

    .p-multiselect:not(.p-disabled):hover {
        border-color: dt('multiselect.hover.border.color');
    }

    .p-multiselect:not(.p-disabled).p-focus {
        border-color: dt('multiselect.focus.border.color');
        box-shadow: dt('multiselect.focus.ring.shadow');
        outline: dt('multiselect.focus.ring.width') dt('multiselect.focus.ring.style') dt('multiselect.focus.ring.color');
        outline-offset: dt('multiselect.focus.ring.offset');
    }

    .p-multiselect.p-variant-filled {
        background: dt('multiselect.filled.background');
    }

    .p-multiselect.p-variant-filled:not(.p-disabled):hover {
        background: dt('multiselect.filled.hover.background');
    }

    .p-multiselect.p-variant-filled.p-focus {
        background: dt('multiselect.filled.focus.background');
    }

    .p-multiselect.p-invalid {
        border-color: dt('multiselect.invalid.border.color');
    }

    .p-multiselect.p-disabled {
        opacity: 1;
        background: dt('multiselect.disabled.background');
    }

    .p-multiselect-dropdown {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        background: transparent;
        color: dt('multiselect.dropdown.color');
        width: dt('multiselect.dropdown.width');
        border-start-end-radius: dt('multiselect.border.radius');
        border-end-end-radius: dt('multiselect.border.radius');
    }

    .p-multiselect-clear-icon {
        align-self: center;
        color: dt('multiselect.clear.icon.color');
        inset-inline-end: dt('multiselect.dropdown.width');
    }

    .p-multiselect-label-container {
        overflow: hidden;
        flex: 1 1 auto;
        cursor: pointer;
    }

    .p-multiselect-label {
        white-space: nowrap;
        cursor: pointer;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: dt('multiselect.padding.y') dt('multiselect.padding.x');
        color: dt('multiselect.color');
    }

    .p-multiselect-display-chip .p-multiselect-label {
        display: flex;
        align-items: center;
        gap: calc(dt('multiselect.padding.y') / 2);
    }

    .p-multiselect-label.p-placeholder {
        color: dt('multiselect.placeholder.color');
    }

    .p-multiselect.p-invalid .p-multiselect-label.p-placeholder {
        color: dt('multiselect.invalid.placeholder.color');
    }

    .p-multiselect.p-disabled .p-multiselect-label {
        color: dt('multiselect.disabled.color');
    }

    .p-multiselect-label-empty {
        overflow: hidden;
        visibility: hidden;
    }

    .p-multiselect-overlay {
        position: absolute;
        top: 0;
        left: 0;
        background: dt('multiselect.overlay.background');
        color: dt('multiselect.overlay.color');
        border: 1px solid dt('multiselect.overlay.border.color');
        border-radius: dt('multiselect.overlay.border.radius');
        box-shadow: dt('multiselect.overlay.shadow');
        min-width: 100%;
    }

    .p-multiselect-header {
        display: flex;
        align-items: center;
        padding: dt('multiselect.list.header.padding');
    }

    .p-multiselect-header .p-checkbox {
        margin-inline-end: dt('multiselect.option.gap');
    }

    .p-multiselect-filter-container {
        flex: 1 1 auto;
    }

    .p-multiselect-filter {
        width: 100%;
    }

    .p-multiselect-list-container {
        overflow: auto;
    }

    .p-multiselect-list {
        margin: 0;
        padding: 0;
        list-style-type: none;
        padding: dt('multiselect.list.padding');
        display: flex;
        flex-direction: column;
        gap: dt('multiselect.list.gap');
    }

    .p-multiselect-option {
        cursor: pointer;
        font-weight: normal;
        white-space: nowrap;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        gap: dt('multiselect.option.gap');
        padding: dt('multiselect.option.padding');
        border: 0 none;
        color: dt('multiselect.option.color');
        background: transparent;
        transition:
            background dt('multiselect.transition.duration'),
            color dt('multiselect.transition.duration'),
            border-color dt('multiselect.transition.duration'),
            box-shadow dt('multiselect.transition.duration'),
            outline-color dt('multiselect.transition.duration');
        border-radius: dt('multiselect.option.border.radius');
    }

    .p-multiselect-option:not(.p-multiselect-option-selected):not(.p-disabled).p-focus {
        background: dt('multiselect.option.focus.background');
        color: dt('multiselect.option.focus.color');
    }

    .p-multiselect-option:not(.p-multiselect-option-selected):not(.p-disabled):hover {
        background: dt('multiselect.option.focus.background');
        color: dt('multiselect.option.focus.color');
    }

    .p-multiselect-option.p-multiselect-option-selected {
        background: dt('multiselect.option.selected.background');
        color: dt('multiselect.option.selected.color');
    }

    .p-multiselect-option.p-multiselect-option-selected.p-focus {
        background: dt('multiselect.option.selected.focus.background');
        color: dt('multiselect.option.selected.focus.color');
    }

    .p-multiselect-option-group {
        cursor: auto;
        margin: 0;
        padding: dt('multiselect.option.group.padding');
        background: dt('multiselect.option.group.background');
        color: dt('multiselect.option.group.color');
        font-weight: dt('multiselect.option.group.font.weight');
    }

    .p-multiselect-empty-message {
        padding: dt('multiselect.empty.message.padding');
    }

    .p-multiselect-label .p-chip {
        padding-block-start: calc(dt('multiselect.padding.y') / 2);
        padding-block-end: calc(dt('multiselect.padding.y') / 2);
        border-radius: dt('multiselect.chip.border.radius');
    }

    .p-multiselect-label:has(.p-chip) {
        padding: calc(dt('multiselect.padding.y') / 2) calc(dt('multiselect.padding.x') / 2);
    }

    .p-multiselect-fluid {
        display: flex;
        width: 100%;
    }

    .p-multiselect-sm .p-multiselect-label {
        font-size: dt('multiselect.sm.font.size');
        padding-block: dt('multiselect.sm.padding.y');
        padding-inline: dt('multiselect.sm.padding.x');
    }

    .p-multiselect-sm .p-multiselect-dropdown .p-icon {
        font-size: dt('multiselect.sm.font.size');
        width: dt('multiselect.sm.font.size');
        height: dt('multiselect.sm.font.size');
    }

    .p-multiselect-lg .p-multiselect-label {
        font-size: dt('multiselect.lg.font.size');
        padding-block: dt('multiselect.lg.padding.y');
        padding-inline: dt('multiselect.lg.padding.x');
    }

    .p-multiselect-lg .p-multiselect-dropdown .p-icon {
        font-size: dt('multiselect.lg.font.size');
        width: dt('multiselect.lg.font.size');
        height: dt('multiselect.lg.font.size');
    }

    .p-floatlabel-in .p-multiselect-filter {
        padding-block-start: dt('multiselect.padding.y');
        padding-block-end: dt('multiselect.padding.y');
    }
`,ht={root:function(t){var i=t.props;return{position:i.appendTo==="self"?"relative":void 0}}},ft={root:function(t){var i=t.instance,n=t.props;return["p-multiselect p-component p-inputwrapper",{"p-multiselect-display-chip":n.display==="chip","p-disabled":n.disabled,"p-invalid":i.$invalid,"p-variant-filled":i.$variant==="filled","p-focus":i.focused,"p-inputwrapper-filled":i.$filled,"p-inputwrapper-focus":i.focused||i.overlayVisible,"p-multiselect-open":i.overlayVisible,"p-multiselect-fluid":i.$fluid,"p-multiselect-sm p-inputfield-sm":n.size==="small","p-multiselect-lg p-inputfield-lg":n.size==="large"}]},labelContainer:"p-multiselect-label-container",label:function(t){var i=t.instance,n=t.props;return["p-multiselect-label",{"p-placeholder":i.label===n.placeholder,"p-multiselect-label-empty":!n.placeholder&&!i.$filled}]},clearIcon:"p-multiselect-clear-icon",chipItem:"p-multiselect-chip-item",pcChip:"p-multiselect-chip",chipIcon:"p-multiselect-chip-icon",dropdown:"p-multiselect-dropdown",loadingIcon:"p-multiselect-loading-icon",dropdownIcon:"p-multiselect-dropdown-icon",overlay:"p-multiselect-overlay p-component",header:"p-multiselect-header",pcFilterContainer:"p-multiselect-filter-container",pcFilter:"p-multiselect-filter",listContainer:"p-multiselect-list-container",list:"p-multiselect-list",optionGroup:"p-multiselect-option-group",option:function(t){var i=t.instance,n=t.option,s=t.index,l=t.getItemOptions,a=t.props;return["p-multiselect-option",{"p-multiselect-option-selected":i.isSelected(n)&&a.highlightOnSelect,"p-focus":i.focusedOptionIndex===i.getOptionIndex(s,l),"p-disabled":i.isOptionDisabled(n)}]},emptyMessage:"p-multiselect-empty-message"},mt=re.extend({name:"multiselect",style:pt,classes:ft,inlineStyles:ht}),bt={name:"BaseMultiSelect",extends:tt,props:{options:Array,optionLabel:null,optionValue:null,optionDisabled:null,optionGroupLabel:null,optionGroupChildren:null,scrollHeight:{type:String,default:"14rem"},placeholder:String,inputId:{type:String,default:null},panelClass:{type:String,default:null},panelStyle:{type:null,default:null},overlayClass:{type:String,default:null},overlayStyle:{type:null,default:null},dataKey:null,showClear:{type:Boolean,default:!1},clearIcon:{type:String,default:void 0},resetFilterOnClear:{type:Boolean,default:!1},filter:Boolean,filterPlaceholder:String,filterLocale:String,filterMatchMode:{type:String,default:"contains"},filterFields:{type:Array,default:null},appendTo:{type:[String,Object],default:"body"},display:{type:String,default:"comma"},selectedItemsLabel:{type:String,default:null},maxSelectedLabels:{type:Number,default:null},selectionLimit:{type:Number,default:null},showToggleAll:{type:Boolean,default:!0},loading:{type:Boolean,default:!1},checkboxIcon:{type:String,default:void 0},dropdownIcon:{type:String,default:void 0},filterIcon:{type:String,default:void 0},loadingIcon:{type:String,default:void 0},removeTokenIcon:{type:String,default:void 0},chipIcon:{type:String,default:void 0},selectAll:{type:Boolean,default:null},resetFilterOnHide:{type:Boolean,default:!1},virtualScrollerOptions:{type:Object,default:null},autoOptionFocus:{type:Boolean,default:!1},autoFilterFocus:{type:Boolean,default:!1},focusOnHover:{type:Boolean,default:!0},highlightOnSelect:{type:Boolean,default:!1},filterMessage:{type:String,default:null},selectionMessage:{type:String,default:null},emptySelectionMessage:{type:String,default:null},emptyFilterMessage:{type:String,default:null},emptyMessage:{type:String,default:null},tabindex:{type:Number,default:0},ariaLabel:{type:String,default:null},ariaLabelledby:{type:String,default:null}},style:mt,provide:function(){return{$pcMultiSelect:this,$parentInstance:this}}};function B(e){"@babel/helpers - typeof";return B=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},B(e)}function te(e,t){var i=Object.keys(e);if(Object.getOwnPropertySymbols){var n=Object.getOwnPropertySymbols(e);t&&(n=n.filter(function(s){return Object.getOwnPropertyDescriptor(e,s).enumerable})),i.push.apply(i,n)}return i}function ie(e){for(var t=1;t<arguments.length;t++){var i=arguments[t]!=null?arguments[t]:{};t%2?te(Object(i),!0).forEach(function(n){V(e,n,i[n])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(i)):te(Object(i)).forEach(function(n){Object.defineProperty(e,n,Object.getOwnPropertyDescriptor(i,n))})}return e}function V(e,t,i){return(t=gt(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function gt(e){var t=yt(e,"string");return B(t)=="symbol"?t:t+""}function yt(e,t){if(B(e)!="object"||!e)return e;var i=e[Symbol.toPrimitive];if(i!==void 0){var n=i.call(e,t);if(B(n)!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(e)}function ne(e){return St(e)||It(e)||Ot(e)||vt()}function vt(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Ot(e,t){if(e){if(typeof e=="string")return X(e,t);var i={}.toString.call(e).slice(8,-1);return i==="Object"&&e.constructor&&(i=e.constructor.name),i==="Map"||i==="Set"?Array.from(e):i==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(i)?X(e,t):void 0}}function It(e){if(typeof Symbol<"u"&&e[Symbol.iterator]!=null||e["@@iterator"]!=null)return Array.from(e)}function St(e){if(Array.isArray(e))return X(e)}function X(e,t){(t==null||t>e.length)&&(t=e.length);for(var i=0,n=Array(t);i<t;i++)n[i]=e[i];return n}var kt={name:"MultiSelect",extends:bt,inheritAttrs:!1,emits:["change","focus","blur","before-show","before-hide","show","hide","filter","selectall-change"],inject:{$pcFluid:{default:null}},outsideClickListener:null,scrollHandler:null,resizeListener:null,overlay:null,list:null,virtualScroller:null,startRangeIndex:-1,searchTimeout:null,searchValue:"",selectOnFocus:!1,data:function(){return{clicked:!1,focused:!1,focusedOptionIndex:-1,filterValue:null,overlayVisible:!1}},watch:{options:function(){this.autoUpdateModel()}},mounted:function(){this.autoUpdateModel()},beforeUnmount:function(){this.unbindOutsideClickListener(),this.unbindResizeListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.overlay&&(Q.clear(this.overlay),this.overlay=null)},methods:{getOptionIndex:function(t,i){return this.virtualScrollerDisabled?t:i&&i(t).index},getOptionLabel:function(t){return this.optionLabel?R(t,this.optionLabel):t},getOptionValue:function(t){return this.optionValue?R(t,this.optionValue):t},getOptionRenderKey:function(t,i){return this.dataKey?R(t,this.dataKey):this.getOptionLabel(t)+"_".concat(i)},getHeaderCheckboxPTOptions:function(t){return this.ptm(t,{context:{selected:this.allSelected}})},getCheckboxPTOptions:function(t,i,n,s){return this.ptm(s,{context:{selected:this.isSelected(t),focused:this.focusedOptionIndex===this.getOptionIndex(n,i),disabled:this.isOptionDisabled(t)}})},isOptionDisabled:function(t){return this.maxSelectionLimitReached&&!this.isSelected(t)?!0:this.optionDisabled?R(t,this.optionDisabled):!1},isOptionGroup:function(t){return!!(this.optionGroupLabel&&t.optionGroup&&t.group)},getOptionGroupLabel:function(t){return R(t,this.optionGroupLabel)},getOptionGroupChildren:function(t){return R(t,this.optionGroupChildren)},getAriaPosInset:function(t){var i=this;return(this.optionGroupLabel?t-this.visibleOptions.slice(0,t).filter(function(n){return i.isOptionGroup(n)}).length:t)+1},show:function(t){this.$emit("before-show"),this.overlayVisible=!0,this.focusedOptionIndex=this.focusedOptionIndex!==-1?this.focusedOptionIndex:this.autoOptionFocus?this.findFirstFocusedOptionIndex():this.findSelectedOptionIndex(),t&&E(this.$refs.focusInput)},hide:function(t){var i=this,n=function(){i.$emit("before-hide"),i.overlayVisible=!1,i.clicked=!1,i.focusedOptionIndex=-1,i.searchValue="",i.resetFilterOnHide&&(i.filterValue=null),t&&E(i.$refs.focusInput)};setTimeout(function(){n()},0)},onFocus:function(t){this.disabled||(this.focused=!0,this.overlayVisible&&(this.focusedOptionIndex=this.focusedOptionIndex!==-1?this.focusedOptionIndex:this.autoOptionFocus?this.findFirstFocusedOptionIndex():this.findSelectedOptionIndex(),!this.autoFilterFocus&&this.scrollInView(this.focusedOptionIndex)),this.$emit("focus",t))},onBlur:function(t){var i,n;this.clicked=!1,this.focused=!1,this.focusedOptionIndex=-1,this.searchValue="",this.$emit("blur",t),(i=(n=this.formField).onBlur)===null||i===void 0||i.call(n)},onKeyDown:function(t){var i=this;if(this.disabled){t.preventDefault();return}var n=t.metaKey||t.ctrlKey;switch(t.code){case"ArrowDown":this.onArrowDownKey(t);break;case"ArrowUp":this.onArrowUpKey(t);break;case"Home":this.onHomeKey(t);break;case"End":this.onEndKey(t);break;case"PageDown":this.onPageDownKey(t);break;case"PageUp":this.onPageUpKey(t);break;case"Enter":case"NumpadEnter":case"Space":this.onEnterKey(t);break;case"Escape":this.onEscapeKey(t);break;case"Tab":this.onTabKey(t);break;case"ShiftLeft":case"ShiftRight":this.onShiftKey(t);break;default:if(t.code==="KeyA"&&n){var s=this.visibleOptions.filter(function(l){return i.isValidOption(l)}).map(function(l){return i.getOptionValue(l)});this.updateModel(t,s),t.preventDefault();break}!n&&Ke(t.key)&&(!this.overlayVisible&&this.show(),this.searchOptions(t),t.preventDefault());break}this.clicked=!1},onContainerClick:function(t){this.disabled||this.loading||t.target.tagName==="INPUT"||t.target.getAttribute("data-pc-section")==="clearicon"||t.target.closest('[data-pc-section="clearicon"]')||((!this.overlay||!this.overlay.contains(t.target))&&(this.overlayVisible?this.hide(!0):this.show(!0)),this.clicked=!0)},onClearClick:function(t){this.updateModel(t,[]),this.resetFilterOnClear&&(this.filterValue=null)},onFirstHiddenFocus:function(t){var i=t.relatedTarget===this.$refs.focusInput?Te(this.overlay,':not([data-p-hidden-focusable="true"])'):this.$refs.focusInput;E(i)},onLastHiddenFocus:function(t){var i=t.relatedTarget===this.$refs.focusInput?Ve(this.overlay,':not([data-p-hidden-focusable="true"])'):this.$refs.focusInput;E(i)},onOptionSelect:function(t,i){var n=this,s=arguments.length>2&&arguments[2]!==void 0?arguments[2]:-1,l=arguments.length>3&&arguments[3]!==void 0?arguments[3]:!1;if(!(this.disabled||this.isOptionDisabled(i))){var a=this.isSelected(i),h=null;a?h=this.d_value.filter(function(p){return!W(p,n.getOptionValue(i),n.equalityKey)}):h=[].concat(ne(this.d_value||[]),[this.getOptionValue(i)]),this.updateModel(t,h),s!==-1&&(this.focusedOptionIndex=s),l&&E(this.$refs.focusInput)}},onOptionMouseMove:function(t,i){this.focusOnHover&&this.changeFocusedOptionIndex(t,i)},onOptionSelectRange:function(t){var i=this,n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:-1,s=arguments.length>2&&arguments[2]!==void 0?arguments[2]:-1;if(n===-1&&(n=this.findNearestSelectedOptionIndex(s,!0)),s===-1&&(s=this.findNearestSelectedOptionIndex(n)),n!==-1&&s!==-1){var l=Math.min(n,s),a=Math.max(n,s),h=this.visibleOptions.slice(l,a+1).filter(function(p){return i.isValidOption(p)}).map(function(p){return i.getOptionValue(p)});this.updateModel(t,h)}},onFilterChange:function(t){var i=t.target.value;this.filterValue=i,this.focusedOptionIndex=-1,this.$emit("filter",{originalEvent:t,value:i}),!this.virtualScrollerDisabled&&this.virtualScroller.scrollToIndex(0)},onFilterKeyDown:function(t){switch(t.code){case"ArrowDown":this.onArrowDownKey(t);break;case"ArrowUp":this.onArrowUpKey(t,!0);break;case"ArrowLeft":case"ArrowRight":this.onArrowLeftKey(t,!0);break;case"Home":this.onHomeKey(t,!0);break;case"End":this.onEndKey(t,!0);break;case"Enter":case"NumpadEnter":this.onEnterKey(t);break;case"Escape":this.onEscapeKey(t);break;case"Tab":this.onTabKey(t,!0);break}},onFilterBlur:function(){this.focusedOptionIndex=-1},onFilterUpdated:function(){this.overlayVisible&&this.alignOverlay()},onOverlayClick:function(t){Ze.emit("overlay-click",{originalEvent:t,target:this.$el})},onOverlayKeyDown:function(t){switch(t.code){case"Escape":this.onEscapeKey(t);break}},onArrowDownKey:function(t){if(!this.overlayVisible)this.show();else{var i=this.focusedOptionIndex!==-1?this.findNextOptionIndex(this.focusedOptionIndex):this.clicked?this.findFirstOptionIndex():this.findFirstFocusedOptionIndex();t.shiftKey&&this.onOptionSelectRange(t,this.startRangeIndex,i),this.changeFocusedOptionIndex(t,i)}t.preventDefault()},onArrowUpKey:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;if(t.altKey&&!i)this.focusedOptionIndex!==-1&&this.onOptionSelect(t,this.visibleOptions[this.focusedOptionIndex]),this.overlayVisible&&this.hide(),t.preventDefault();else{var n=this.focusedOptionIndex!==-1?this.findPrevOptionIndex(this.focusedOptionIndex):this.clicked?this.findLastOptionIndex():this.findLastFocusedOptionIndex();t.shiftKey&&this.onOptionSelectRange(t,n,this.startRangeIndex),this.changeFocusedOptionIndex(t,n),!this.overlayVisible&&this.show(),t.preventDefault()}},onArrowLeftKey:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;i&&(this.focusedOptionIndex=-1)},onHomeKey:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;if(i){var n=t.currentTarget;t.shiftKey?n.setSelectionRange(0,t.target.selectionStart):(n.setSelectionRange(0,0),this.focusedOptionIndex=-1)}else{var s=t.metaKey||t.ctrlKey,l=this.findFirstOptionIndex();t.shiftKey&&s&&this.onOptionSelectRange(t,l,this.startRangeIndex),this.changeFocusedOptionIndex(t,l),!this.overlayVisible&&this.show()}t.preventDefault()},onEndKey:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;if(i){var n=t.currentTarget;if(t.shiftKey)n.setSelectionRange(t.target.selectionStart,n.value.length);else{var s=n.value.length;n.setSelectionRange(s,s),this.focusedOptionIndex=-1}}else{var l=t.metaKey||t.ctrlKey,a=this.findLastOptionIndex();t.shiftKey&&l&&this.onOptionSelectRange(t,this.startRangeIndex,a),this.changeFocusedOptionIndex(t,a),!this.overlayVisible&&this.show()}t.preventDefault()},onPageUpKey:function(t){this.scrollInView(0),t.preventDefault()},onPageDownKey:function(t){this.scrollInView(this.visibleOptions.length-1),t.preventDefault()},onEnterKey:function(t){this.overlayVisible?this.focusedOptionIndex!==-1&&(t.shiftKey?this.onOptionSelectRange(t,this.focusedOptionIndex):this.onOptionSelect(t,this.visibleOptions[this.focusedOptionIndex])):(this.focusedOptionIndex=-1,this.onArrowDownKey(t)),t.preventDefault()},onEscapeKey:function(t){this.overlayVisible&&(this.hide(!0),t.stopPropagation()),t.preventDefault()},onTabKey:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;i||(this.overlayVisible&&this.hasFocusableElements()?(E(t.shiftKey?this.$refs.lastHiddenFocusableElementOnOverlay:this.$refs.firstHiddenFocusableElementOnOverlay),t.preventDefault()):(this.focusedOptionIndex!==-1&&this.onOptionSelect(t,this.visibleOptions[this.focusedOptionIndex]),this.overlayVisible&&this.hide(this.filter)))},onShiftKey:function(){this.startRangeIndex=this.focusedOptionIndex},onOverlayEnter:function(t){Q.set("overlay",t,this.$primevue.config.zIndex.overlay),Fe(t,{position:"absolute",top:"0"}),this.alignOverlay(),this.scrollInView(),this.autoFilterFocus&&E(this.$refs.filterInput.$el),this.autoUpdateModel(),this.$attrSelector&&t.setAttribute(this.$attrSelector,"")},onOverlayAfterEnter:function(){this.bindOutsideClickListener(),this.bindScrollListener(),this.bindResizeListener(),this.$emit("show")},onOverlayLeave:function(t){t.style.pointerEvents="none",this.unbindOutsideClickListener(),this.unbindScrollListener(),this.unbindResizeListener(),this.$emit("hide"),this.overlay=null},onOverlayAfterLeave:function(t){Q.clear(t)},alignOverlay:function(){this.appendTo==="self"?Le(this.overlay,this.$el):(this.overlay.style.minWidth=xe(this.$el)+"px",Ce(this.overlay,this.$el))},bindOutsideClickListener:function(){var t=this;this.outsideClickListener||(this.outsideClickListener=function(i){t.overlayVisible&&t.isOutsideClicked(i)&&t.hide()},document.addEventListener("click",this.outsideClickListener,!0))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener,!0),this.outsideClickListener=null)},bindScrollListener:function(){var t=this;this.scrollHandler||(this.scrollHandler=new Xe(this.$refs.container,function(){t.overlayVisible&&t.hide()})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var t=this;this.resizeListener||(this.resizeListener=function(){t.overlayVisible&&!we()&&t.hide()},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},isOutsideClicked:function(t){return!(this.$el.isSameNode(t.target)||this.$el.contains(t.target)||this.overlay&&this.overlay.contains(t.target))},getLabelByValue:function(t){var i=this,n=this.optionGroupLabel?this.flatOptions(this.options):this.options||[],s=n.find(function(l){return!i.isOptionGroup(l)&&W(i.getOptionValue(l),t,i.equalityKey)});return this.getOptionLabel(s)},getSelectedItemsLabel:function(){var t=/{(.*?)}/,i=this.selectedItemsLabel||this.$primevue.config.locale.selectionMessage;return t.test(i)?i.replace(i.match(t)[0],this.d_value.length+""):i},onToggleAll:function(t){var i=this;if(this.selectAll!==null)this.$emit("selectall-change",{originalEvent:t,checked:!this.allSelected});else{var n=this.allSelected?[]:this.visibleOptions.filter(function(s){return i.isValidOption(s)}).map(function(s){return i.getOptionValue(s)});this.updateModel(t,n)}},removeOption:function(t,i){var n=this;t.stopPropagation();var s=this.d_value.filter(function(l){return!W(l,i,n.equalityKey)});this.updateModel(t,s)},clearFilter:function(){this.filterValue=null},hasFocusableElements:function(){return ke(this.overlay,':not([data-p-hidden-focusable="true"])').length>0},isOptionMatched:function(t){var i;return this.isValidOption(t)&&typeof this.getOptionLabel(t)=="string"&&((i=this.getOptionLabel(t))===null||i===void 0?void 0:i.toLocaleLowerCase(this.filterLocale).startsWith(this.searchValue.toLocaleLowerCase(this.filterLocale)))},isValidOption:function(t){return D(t)&&!(this.isOptionDisabled(t)||this.isOptionGroup(t))},isValidSelectedOption:function(t){return this.isValidOption(t)&&this.isSelected(t)},isEquals:function(t,i){return W(t,i,this.equalityKey)},isSelected:function(t){var i=this,n=this.getOptionValue(t);return(this.d_value||[]).some(function(s){return i.isEquals(s,n)})},findFirstOptionIndex:function(){var t=this;return this.visibleOptions.findIndex(function(i){return t.isValidOption(i)})},findLastOptionIndex:function(){var t=this;return q(this.visibleOptions,function(i){return t.isValidOption(i)})},findNextOptionIndex:function(t){var i=this,n=t<this.visibleOptions.length-1?this.visibleOptions.slice(t+1).findIndex(function(s){return i.isValidOption(s)}):-1;return n>-1?n+t+1:t},findPrevOptionIndex:function(t){var i=this,n=t>0?q(this.visibleOptions.slice(0,t),function(s){return i.isValidOption(s)}):-1;return n>-1?n:t},findSelectedOptionIndex:function(){var t=this;if(this.$filled){for(var i=function(){var a=t.d_value[s],h=t.visibleOptions.findIndex(function(p){return t.isValidSelectedOption(p)&&t.isEquals(a,t.getOptionValue(p))});if(h>-1)return{v:h}},n,s=this.d_value.length-1;s>=0;s--)if(n=i(),n)return n.v}return-1},findFirstSelectedOptionIndex:function(){var t=this;return this.$filled?this.visibleOptions.findIndex(function(i){return t.isValidSelectedOption(i)}):-1},findLastSelectedOptionIndex:function(){var t=this;return this.$filled?q(this.visibleOptions,function(i){return t.isValidSelectedOption(i)}):-1},findNextSelectedOptionIndex:function(t){var i=this,n=this.$filled&&t<this.visibleOptions.length-1?this.visibleOptions.slice(t+1).findIndex(function(s){return i.isValidSelectedOption(s)}):-1;return n>-1?n+t+1:-1},findPrevSelectedOptionIndex:function(t){var i=this,n=this.$filled&&t>0?q(this.visibleOptions.slice(0,t),function(s){return i.isValidSelectedOption(s)}):-1;return n>-1?n:-1},findNearestSelectedOptionIndex:function(t){var i=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,n=-1;return this.$filled&&(i?(n=this.findPrevSelectedOptionIndex(t),n=n===-1?this.findNextSelectedOptionIndex(t):n):(n=this.findNextSelectedOptionIndex(t),n=n===-1?this.findPrevSelectedOptionIndex(t):n)),n>-1?n:t},findFirstFocusedOptionIndex:function(){var t=this.findFirstSelectedOptionIndex();return t<0?this.findFirstOptionIndex():t},findLastFocusedOptionIndex:function(){var t=this.findSelectedOptionIndex();return t<0?this.findLastOptionIndex():t},searchOptions:function(t){var i=this;this.searchValue=(this.searchValue||"")+t.key;var n=-1;D(this.searchValue)&&(this.focusedOptionIndex!==-1?(n=this.visibleOptions.slice(this.focusedOptionIndex).findIndex(function(s){return i.isOptionMatched(s)}),n=n===-1?this.visibleOptions.slice(0,this.focusedOptionIndex).findIndex(function(s){return i.isOptionMatched(s)}):n+this.focusedOptionIndex):n=this.visibleOptions.findIndex(function(s){return i.isOptionMatched(s)}),n===-1&&this.focusedOptionIndex===-1&&(n=this.findFirstFocusedOptionIndex()),n!==-1&&this.changeFocusedOptionIndex(t,n)),this.searchTimeout&&clearTimeout(this.searchTimeout),this.searchTimeout=setTimeout(function(){i.searchValue="",i.searchTimeout=null},500)},changeFocusedOptionIndex:function(t,i){this.focusedOptionIndex!==i&&(this.focusedOptionIndex=i,this.scrollInView(),this.selectOnFocus&&this.onOptionSelect(t,this.visibleOptions[i]))},scrollInView:function(){var t=this,i=arguments.length>0&&arguments[0]!==void 0?arguments[0]:-1;this.$nextTick(function(){var n=i!==-1?"".concat(t.$id,"_").concat(i):t.focusedOptionId,s=Se(t.list,'li[id="'.concat(n,'"]'));s?s.scrollIntoView&&s.scrollIntoView({block:"nearest",inline:"nearest"}):t.virtualScrollerDisabled||t.virtualScroller&&t.virtualScroller.scrollToIndex(i!==-1?i:t.focusedOptionIndex)})},autoUpdateModel:function(){if(this.autoOptionFocus&&(this.focusedOptionIndex=this.findFirstFocusedOptionIndex()),this.selectOnFocus&&this.autoOptionFocus&&!this.$filled){var t=this.getOptionValue(this.visibleOptions[this.focusedOptionIndex]);this.updateModel(null,[t])}},updateModel:function(t,i){this.writeValue(i,t),this.$emit("change",{originalEvent:t,value:i})},flatOptions:function(t){var i=this;return(t||[]).reduce(function(n,s,l){var a=i.getOptionGroupChildren(s);return a&&Array.isArray(a)?(n.push({optionGroup:s,group:!0,index:l}),a.forEach(function(h){return n.push(h)})):n.push(s),n},[])},overlayRef:function(t){this.overlay=t},listRef:function(t,i){this.list=t,i&&i(t)},virtualScrollerRef:function(t){this.virtualScroller=t}},computed:{visibleOptions:function(){var t=this,i=this.optionGroupLabel?this.flatOptions(this.options):this.options||[];if(this.filterValue){var n=Ie.filter(i,this.searchFields,this.filterValue,this.filterMatchMode,this.filterLocale);if(this.optionGroupLabel){var s=this.options||[],l=[];return s.forEach(function(a){var h=t.getOptionGroupChildren(a),p=h.filter(function(d){return n.includes(d)});p.length>0&&l.push(ie(ie({},a),{},V({},typeof t.optionGroupChildren=="string"?t.optionGroupChildren:"items",ne(p))))}),this.flatOptions(l)}return n}return i},label:function(){var t;if(this.d_value&&this.d_value.length)if(this.loading&&(!this.options||this.options.length===0))t=this.placeholder;else{if(D(this.maxSelectedLabels)&&this.d_value.length>this.maxSelectedLabels)return this.getSelectedItemsLabel();t="";for(var i=0;i<this.d_value.length;i++)i!==0&&(t+=", "),t+=this.getLabelByValue(this.d_value[i])}else t=this.placeholder;return t},chipSelectedItems:function(){return D(this.maxSelectedLabels)&&this.d_value&&this.d_value.length>this.maxSelectedLabels},allSelected:function(){var t=this;return this.selectAll!==null?this.selectAll:D(this.visibleOptions)&&this.visibleOptions.every(function(i){return t.isOptionGroup(i)||t.isOptionDisabled(i)||t.isSelected(i)})},hasSelectedOption:function(){return this.$filled},equalityKey:function(){return this.optionValue?null:this.dataKey},searchFields:function(){return this.filterFields||[this.optionLabel]},maxSelectionLimitReached:function(){return this.selectionLimit&&this.d_value&&this.d_value.length===this.selectionLimit},filterResultMessageText:function(){return D(this.visibleOptions)?this.filterMessageText.replaceAll("{0}",this.visibleOptions.length):this.emptyFilterMessageText},filterMessageText:function(){return this.filterMessage||this.$primevue.config.locale.searchMessage||""},emptyFilterMessageText:function(){return this.emptyFilterMessage||this.$primevue.config.locale.emptySearchMessage||this.$primevue.config.locale.emptyFilterMessage||""},emptyMessageText:function(){return this.emptyMessage||this.$primevue.config.locale.emptyMessage||""},selectionMessageText:function(){return this.selectionMessage||this.$primevue.config.locale.selectionMessage||""},emptySelectionMessageText:function(){return this.emptySelectionMessage||this.$primevue.config.locale.emptySelectionMessage||""},selectedMessageText:function(){return this.$filled?this.selectionMessageText.replaceAll("{0}",this.d_value.length):this.emptySelectionMessageText},focusedOptionId:function(){return this.focusedOptionIndex!==-1?"".concat(this.$id,"_").concat(this.focusedOptionIndex):null},ariaSetSize:function(){var t=this;return this.visibleOptions.filter(function(i){return!t.isOptionGroup(i)}).length},toggleAllAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria[this.allSelected?"selectAll":"unselectAll"]:void 0},listAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.listLabel:void 0},virtualScrollerDisabled:function(){return!this.virtualScrollerOptions},hasFluid:function(){return Oe(this.fluid)?!!this.$pcFluid:this.fluid},isClearIconVisible:function(){return this.showClear&&this.d_value&&this.d_value.length&&this.d_value!=null&&D(this.options)&&!this.disabled&&!this.loading},containerDataP:function(){return $(V({invalid:this.$invalid,disabled:this.disabled,focus:this.focused,fluid:this.$fluid,filled:this.$variant==="filled"},this.size,this.size))},labelDataP:function(){return $(V(V(V({placeholder:this.label===this.placeholder,clearable:this.showClear,disabled:this.disabled},this.size,this.size),"has-chip",this.display==="chip"&&this.d_value&&this.d_value.length&&(this.maxSelectedLabels?this.d_value.length<=this.maxSelectedLabels:!0)),"empty",!this.placeholder&&!this.$filled))},dropdownIconDataP:function(){return $(V({},this.size,this.size))},overlayDataP:function(){return $(V({},"portal-"+this.appendTo,"portal-"+this.appendTo))}},directives:{ripple:ve},components:{InputText:et,Checkbox:Qe,VirtualScroller:Ye,Portal:ye,Chip:ae,IconField:Je,InputIcon:We,TimesIcon:ge,SearchIcon:qe,ChevronDownIcon:Ue,SpinnerIcon:be,CheckIcon:me}};function H(e){"@babel/helpers - typeof";return H=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},H(e)}function le(e,t,i){return(t=wt(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function wt(e){var t=Lt(e,"string");return H(t)=="symbol"?t:t+""}function Lt(e,t){if(H(e)!="object"||!e)return e;var i=e[Symbol.toPrimitive];if(i!==void 0){var n=i.call(e,t);if(H(n)!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(e)}var xt=["data-p"],Ct=["id","disabled","placeholder","tabindex","aria-label","aria-labelledby","aria-expanded","aria-controls","aria-activedescendant","aria-invalid"],Ft=["data-p"],Vt={key:1},Tt=["data-p"],Kt=["id","aria-label"],Mt=["id"],Dt=["id","aria-label","aria-selected","aria-disabled","aria-setsize","aria-posinset","onClick","onMousemove","data-p-selected","data-p-focused","data-p-disabled"];function Et(e,t,i,n,s,l){var a=C("Chip"),h=C("SpinnerIcon"),p=C("Checkbox"),d=C("InputText"),k=C("SearchIcon"),O=C("InputIcon"),j=C("IconField"),G=C("VirtualScroller"),ue=C("Portal"),ce=Me("ripple");return r(),u("div",o({ref:"container",class:e.cx("root"),style:e.sx("root"),onClick:t[7]||(t[7]=function(){return l.onContainerClick&&l.onContainerClick.apply(l,arguments)}),"data-p":l.containerDataP},e.ptmi("root")),[w("div",o({class:"p-hidden-accessible"},e.ptm("hiddenInputContainer"),{"data-p-hidden-accessible":!0}),[w("input",o({ref:"focusInput",id:e.inputId,type:"text",readonly:"",disabled:e.disabled,placeholder:e.placeholder,tabindex:e.disabled?-1:e.tabindex,role:"combobox","aria-label":e.ariaLabel,"aria-labelledby":e.ariaLabelledby,"aria-haspopup":"listbox","aria-expanded":s.overlayVisible,"aria-controls":s.overlayVisible?e.$id+"_list":void 0,"aria-activedescendant":s.focused?l.focusedOptionId:void 0,"aria-invalid":e.invalid||void 0,onFocus:t[0]||(t[0]=function(){return l.onFocus&&l.onFocus.apply(l,arguments)}),onBlur:t[1]||(t[1]=function(){return l.onBlur&&l.onBlur.apply(l,arguments)}),onKeydown:t[2]||(t[2]=function(){return l.onKeyDown&&l.onKeyDown.apply(l,arguments)})},e.ptm("hiddenInput")),null,16,Ct)],16),w("div",o({class:e.cx("labelContainer")},e.ptm("labelContainer")),[w("div",o({class:e.cx("label"),"data-p":l.labelDataP},e.ptm("label")),[b(e.$slots,"value",{value:e.d_value,placeholder:e.placeholder},function(){return[e.display==="comma"?(r(),u(A,{key:0},[K(g(l.label||"empty"),1)],64)):e.display==="chip"?(r(),u(A,{key:1},[e.loading&&(!e.options||e.options.length===0)?(r(),u(A,{key:0},[K(g(e.placeholder||"empty"),1)],64)):l.chipSelectedItems?(r(),u("span",Vt,g(l.label),1)):(r(!0),u(A,{key:2},_(e.d_value,function(c,z){return r(),u("span",o({key:"chip-".concat(l.getLabelByValue(c),"_").concat(z),class:e.cx("chipItem")},{ref_for:!0},e.ptm("chipItem")),[b(e.$slots,"chip",{value:c,removeCallback:function(L){return l.removeOption(L,c)}},function(){return[x(a,{class:F(e.cx("pcChip")),label:l.getLabelByValue(c),removeIcon:e.chipIcon||e.removeTokenIcon,removable:"",unstyled:e.unstyled,onRemove:function(L){return l.removeOption(L,c)},pt:e.ptm("pcChip")},{removeicon:S(function(){return[b(e.$slots,e.$slots.chipicon?"chipicon":"removetokenicon",{class:F(e.cx("chipIcon")),item:c,removeCallback:function(L){return l.removeOption(L,c)}})]}),_:2},1032,["class","label","removeIcon","unstyled","onRemove","pt"])]})],16)}),128)),!e.d_value||e.d_value.length===0?(r(),u(A,{key:3},[K(g(e.placeholder||"empty"),1)],64)):m("",!0)],64)):m("",!0)]})],16,Ft)],16),l.isClearIconVisible?b(e.$slots,"clearicon",{key:0,class:F(e.cx("clearIcon")),clearCallback:l.onClearClick},function(){return[(r(),v(T(e.clearIcon?"i":"TimesIcon"),o({ref:"clearIcon",class:[e.cx("clearIcon"),e.clearIcon],onClick:l.onClearClick},e.ptm("clearIcon"),{"data-pc-section":"clearicon"}),null,16,["class","onClick"]))]}):m("",!0),w("div",o({class:e.cx("dropdown")},e.ptm("dropdown")),[e.loading?b(e.$slots,"loadingicon",{key:0,class:F(e.cx("loadingIcon"))},function(){return[e.loadingIcon?(r(),u("span",o({key:0,class:[e.cx("loadingIcon"),"pi-spin",e.loadingIcon],"aria-hidden":"true"},e.ptm("loadingIcon")),null,16)):(r(),v(h,o({key:1,class:e.cx("loadingIcon"),spin:"","aria-hidden":"true"},e.ptm("loadingIcon")),null,16,["class"]))]}):b(e.$slots,"dropdownicon",{key:1,class:F(e.cx("dropdownIcon"))},function(){return[(r(),v(T(e.dropdownIcon?"span":"ChevronDownIcon"),o({class:[e.cx("dropdownIcon"),e.dropdownIcon],"aria-hidden":"true","data-p":l.dropdownIconDataP},e.ptm("dropdownIcon")),null,16,["class","data-p"]))]})],16),x(ue,{appendTo:e.appendTo},{default:S(function(){return[x(De,o({name:"p-anchored-overlay",onEnter:l.onOverlayEnter,onAfterEnter:l.onOverlayAfterEnter,onLeave:l.onOverlayLeave,onAfterLeave:l.onOverlayAfterLeave},e.ptm("transition")),{default:S(function(){return[s.overlayVisible?(r(),u("div",o({key:0,ref:l.overlayRef,style:[e.panelStyle,e.overlayStyle],class:[e.cx("overlay"),e.panelClass,e.overlayClass],onClick:t[5]||(t[5]=function(){return l.onOverlayClick&&l.onOverlayClick.apply(l,arguments)}),onKeydown:t[6]||(t[6]=function(){return l.onOverlayKeyDown&&l.onOverlayKeyDown.apply(l,arguments)}),"data-p":l.overlayDataP},e.ptm("overlay")),[w("span",o({ref:"firstHiddenFocusableElementOnOverlay",role:"presentation","aria-hidden":"true",class:"p-hidden-accessible p-hidden-focusable",tabindex:0,onFocus:t[3]||(t[3]=function(){return l.onFirstHiddenFocus&&l.onFirstHiddenFocus.apply(l,arguments)})},e.ptm("hiddenFirstFocusableEl"),{"data-p-hidden-accessible":!0,"data-p-hidden-focusable":!0}),null,16),b(e.$slots,"header",{value:e.d_value,options:l.visibleOptions}),e.showToggleAll&&e.selectionLimit==null||e.filter?(r(),u("div",o({key:0,class:e.cx("header")},e.ptm("header")),[e.showToggleAll&&e.selectionLimit==null?(r(),v(p,{key:0,modelValue:l.allSelected,binary:!0,disabled:e.disabled,variant:e.variant,"aria-label":l.toggleAllAriaLabel,onChange:l.onToggleAll,unstyled:e.unstyled,pt:l.getHeaderCheckboxPTOptions("pcHeaderCheckbox"),formControl:{novalidate:!0}},{icon:S(function(c){return[e.$slots.headercheckboxicon?(r(),v(T(e.$slots.headercheckboxicon),{key:0,checked:c.checked,class:F(c.class)},null,8,["checked","class"])):c.checked?(r(),v(T(e.checkboxIcon?"span":"CheckIcon"),o({key:1,class:[c.class,le({},e.checkboxIcon,c.checked)]},l.getHeaderCheckboxPTOptions("pcHeaderCheckbox.icon")),null,16,["class"])):m("",!0)]}),_:1},8,["modelValue","disabled","variant","aria-label","onChange","unstyled","pt"])):m("",!0),e.filter?(r(),v(j,{key:1,class:F(e.cx("pcFilterContainer")),unstyled:e.unstyled,pt:e.ptm("pcFilterContainer")},{default:S(function(){return[x(d,{ref:"filterInput",value:s.filterValue,onVnodeMounted:l.onFilterUpdated,onVnodeUpdated:l.onFilterUpdated,class:F(e.cx("pcFilter")),placeholder:e.filterPlaceholder,disabled:e.disabled,variant:e.variant,unstyled:e.unstyled,role:"searchbox",autocomplete:"off","aria-owns":e.$id+"_list","aria-activedescendant":l.focusedOptionId,onKeydown:l.onFilterKeyDown,onBlur:l.onFilterBlur,onInput:l.onFilterChange,pt:e.ptm("pcFilter"),formControl:{novalidate:!0}},null,8,["value","onVnodeMounted","onVnodeUpdated","class","placeholder","disabled","variant","unstyled","aria-owns","aria-activedescendant","onKeydown","onBlur","onInput","pt"]),x(O,{unstyled:e.unstyled,pt:e.ptm("pcFilterIconContainer")},{default:S(function(){return[b(e.$slots,"filtericon",{},function(){return[e.filterIcon?(r(),u("span",o({key:0,class:e.filterIcon},e.ptm("filterIcon")),null,16)):(r(),v(k,Ee(o({key:1},e.ptm("filterIcon"))),null,16))]})]}),_:3},8,["unstyled","pt"])]}),_:3},8,["class","unstyled","pt"])):m("",!0),e.filter?(r(),u("span",o({key:2,role:"status","aria-live":"polite",class:"p-hidden-accessible"},e.ptm("hiddenFilterResult"),{"data-p-hidden-accessible":!0}),g(l.filterResultMessageText),17)):m("",!0)],16)):m("",!0),w("div",o({class:e.cx("listContainer"),style:{"max-height":l.virtualScrollerDisabled?e.scrollHeight:""}},e.ptm("listContainer")),[x(G,o({ref:l.virtualScrollerRef},e.virtualScrollerOptions,{items:l.visibleOptions,style:{height:e.scrollHeight},tabindex:-1,disabled:l.virtualScrollerDisabled,pt:e.ptm("virtualScroller")}),Ae({content:S(function(c){var z=c.styleClass,N=c.contentRef,L=c.items,I=c.getItemOptions,pe=c.contentStyle,U=c.itemSize;return[w("ul",o({ref:function(y){return l.listRef(y,N)},id:e.$id+"_list",class:[e.cx("list"),z],style:pe,role:"listbox","aria-multiselectable":"true","aria-label":l.listAriaLabel},e.ptm("list")),[(r(!0),u(A,null,_(L,function(f,y){return r(),u(A,{key:l.getOptionRenderKey(f,l.getOptionIndex(y,I))},[l.isOptionGroup(f)?(r(),u("li",o({key:0,id:e.$id+"_"+l.getOptionIndex(y,I),style:{height:U?U+"px":void 0},class:e.cx("optionGroup"),role:"option"},{ref_for:!0},e.ptm("optionGroup")),[b(e.$slots,"optiongroup",{option:f.optionGroup,index:l.getOptionIndex(y,I)},function(){return[K(g(l.getOptionGroupLabel(f.optionGroup)),1)]})],16,Mt)):Pe((r(),u("li",o({key:1,id:e.$id+"_"+l.getOptionIndex(y,I),style:{height:U?U+"px":void 0},class:e.cx("option",{option:f,index:y,getItemOptions:I}),role:"option","aria-label":l.getOptionLabel(f),"aria-selected":l.isSelected(f),"aria-disabled":l.isOptionDisabled(f),"aria-setsize":l.ariaSetSize,"aria-posinset":l.getAriaPosInset(l.getOptionIndex(y,I)),onClick:function(Y){return l.onOptionSelect(Y,f,l.getOptionIndex(y,I),!0)},onMousemove:function(Y){return l.onOptionMouseMove(Y,l.getOptionIndex(y,I))}},{ref_for:!0},l.getCheckboxPTOptions(f,I,y,"option"),{"data-p-selected":l.isSelected(f),"data-p-focused":s.focusedOptionIndex===l.getOptionIndex(y,I),"data-p-disabled":l.isOptionDisabled(f)}),[x(p,{defaultValue:l.isSelected(f),binary:!0,tabindex:-1,variant:e.variant,unstyled:e.unstyled,pt:l.getCheckboxPTOptions(f,I,y,"pcOptionCheckbox"),formControl:{novalidate:!0}},{icon:S(function(M){return[e.$slots.optioncheckboxicon||e.$slots.itemcheckboxicon?(r(),v(T(e.$slots.optioncheckboxicon||e.$slots.itemcheckboxicon),{key:0,checked:M.checked,class:F(M.class)},null,8,["checked","class"])):M.checked?(r(),v(T(e.checkboxIcon?"span":"CheckIcon"),o({key:1,class:[M.class,le({},e.checkboxIcon,M.checked)]},{ref_for:!0},l.getCheckboxPTOptions(f,I,y,"pcOptionCheckbox.icon")),null,16,["class"])):m("",!0)]}),_:2},1032,["defaultValue","variant","unstyled","pt"]),b(e.$slots,"option",{option:f,selected:l.isSelected(f),index:l.getOptionIndex(y,I)},function(){return[w("span",o({ref_for:!0},e.ptm("optionLabel")),g(l.getOptionLabel(f)),17)]})],16,Dt)),[[ce]])],64)}),128)),s.filterValue&&(!L||L&&L.length===0)?(r(),u("li",o({key:0,class:e.cx("emptyMessage"),role:"option"},e.ptm("emptyMessage")),[b(e.$slots,"emptyfilter",{},function(){return[K(g(l.emptyFilterMessageText),1)]})],16)):!e.options||e.options&&e.options.length===0?(r(),u("li",o({key:1,class:e.cx("emptyMessage"),role:"option"},e.ptm("emptyMessage")),[b(e.$slots,"empty",{},function(){return[K(g(l.emptyMessageText),1)]})],16)):m("",!0)],16,Kt)]}),_:2},[e.$slots.loader?{name:"loader",fn:S(function(c){var z=c.options;return[b(e.$slots,"loader",{options:z})]}),key:"0"}:void 0]),1040,["items","style","disabled","pt"])],16),b(e.$slots,"footer",{value:e.d_value,options:l.visibleOptions}),!e.options||e.options&&e.options.length===0?(r(),u("span",o({key:1,role:"status","aria-live":"polite",class:"p-hidden-accessible"},e.ptm("hiddenEmptyMessage"),{"data-p-hidden-accessible":!0}),g(l.emptyMessageText),17)):m("",!0),w("span",o({role:"status","aria-live":"polite",class:"p-hidden-accessible"},e.ptm("hiddenSelectedMessage"),{"data-p-hidden-accessible":!0}),g(l.selectedMessageText),17),w("span",o({ref:"lastHiddenFocusableElementOnOverlay",role:"presentation","aria-hidden":"true",class:"p-hidden-accessible p-hidden-focusable",tabindex:0,onFocus:t[4]||(t[4]=function(){return l.onLastHiddenFocus&&l.onLastHiddenFocus.apply(l,arguments)})},e.ptm("hiddenLastFocusableEl"),{"data-p-hidden-accessible":!0,"data-p-hidden-focusable":!0}),null,16)],16,Tt)):m("",!0)]}),_:3},16,["onEnter","onAfterEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo"])],16,xt)}kt.render=Et;function se(e){return e===""||e==="true"||e==="false"||e==="null"||/^-?\d+(?:\.\d+)?$/.test(e)||/[:#\n\r\t|>&*!?[\]{},]/.test(e)||e.startsWith(" ")||e.endsWith(" ")?JSON.stringify(e):e}function Z(e,t=0){const i="  ".repeat(t);if(e==null)return"null";if(typeof e=="boolean"||typeof e=="number")return String(e);if(typeof e=="string")return se(e);if(Array.isArray(e))return e.length?e.map(n=>{const s=Z(n,t+1);return s.includes(`
`)?`${i}-
${s}`:`${i}- ${s}`}).join(`
`):"[]";if(typeof e=="object"){const n=Object.entries(e);return n.length?n.map(([s,l])=>{const a=Z(l,t+1);return a.includes(`
`)?`${i}${s}:
${a}`:`${i}${s}: ${a}`}).join(`
`):"{}"}return se(String(e))}function Qt(e){if(!e)return!1;if(e.parsed!=null)return!0;const t=(e.core||"").replace(/_/g,"-");return it(t)}function Xt(e,t,i,n){if(!e)return"";if(t==="yaml"){const s=e.config_yaml||e.clash_yaml;if(s)return s;if(e.parsed!=null)return Z(e.parsed)}return e.parsed!=null?i(e.parsed):n(e.rendered||"")}function At(e){const t=e.match(/<string>:(\d+)/),i=e.match(/column (\d+)/);return{line:t?Number(t[1]):null,column:i?Number(i[1]):null}}function Pt(e){const t=e.message.indexOf(": ");return t>=0?e.message.slice(t+2):e.message}function de(e,t,i){var h,p;const{line:n,column:s}=At(e),l=n?"json5":"jinja",a=l==="json5"?(t==null?void 0:t.rendered)||"":((h=t==null?void 0:t.error_detail)==null?void 0:h.template_source)||((p=t==null?void 0:t.error_detail)==null?void 0:p.source)||(t==null?void 0:t.rendered)||"";return{message:e,source:a,phase:l,line:n,column:s,label:i||(t==null?void 0:t.label)||(t==null?void 0:t.core)||null}}function Zt(e,t){const i=Pt(e),n=e.detail??null;return n&&n.message===i?n:n&&(t!=null&&t.error_detail)&&t.error_detail.message===i?t.error_detail:i?de(i,t,n==null?void 0:n.label):n}function _t(e){if(!(e!=null&&e.error))return null;const t=e.error_detail;return t&&t.message===e.error?t:de(e.error,e)}function Rt(e){return e?!!(e.source||e.excerpt||e.template_source||e.template_excerpt||e.message):!1}const zt={key:0,class:"flex flex-col gap-3"},$t={class:"flex flex-wrap items-center gap-3 text-sm text-surface-500"},Bt={key:0},Ht={key:1},jt=Re({__name:"RenderErrorDetailDialog",props:He({detail:{}},{visible:{type:Boolean,default:!1},visibleModifiers:{}}),emits:["update:visible"],setup(e){const t=ze(e,"visible"),i=e,{t:n}=oe(),s=je("rendered");$e(()=>i.detail,d=>{s.value=d!=null&&d.template_source?"template":"rendered"},{immediate:!0});const l=J(()=>{var k,O;const d=(O=(k=i.detail)==null?void 0:k.label)==null?void 0:O.trim();return d?n("proxy.renderErrorDetailTitle",{label:d}):n("proxy.renderErrorDetail")}),a=J(()=>{var k,O,j,G;const d=[];return((k=i.detail)!=null&&k.source||(O=i.detail)!=null&&O.excerpt)&&d.push({value:"rendered",label:n("proxy.renderErrorRenderedSource")}),((j=i.detail)!=null&&j.template_source||(G=i.detail)!=null&&G.template_excerpt)&&d.push({value:"template",label:n("proxy.renderErrorTemplateSource")}),d}),h=J(()=>{const d=i.detail;return d?s.value==="template"?d.template_source||d.template_excerpt||"":d.source||d.excerpt||"":""}),p=J(()=>{const d=i.detail;return d!=null&&d.line?d.column?`Line ${d.line}, column ${d.column}`:`Line ${d.line}`:""});return(d,k)=>(r(),v(P(Be),{visible:t.value,"onUpdate:visible":k[1]||(k[1]=O=>t.value=O),modal:"","append-to":"body",class:"w-full max-w-4xl",header:l.value,draggable:!1},{default:S(()=>[e.detail&&P(Rt)(e.detail)?(r(),u("div",zt,[x(P(ee),{severity:"error",closable:!1},{default:S(()=>[K(g(e.detail.message),1)]),_:1}),w("div",$t,[e.detail.phase?(r(),u("span",Bt,g(e.detail.phase),1)):m("",!0),p.value?(r(),u("span",Ht,g(p.value),1)):m("",!0)]),a.value.length>1?(r(),v(P(_e),{key:0,modelValue:s.value,"onUpdate:modelValue":k[0]||(k[0]=O=>s.value=O),options:a.value,"option-label":"label","option-value":"value",class:"w-full max-w-sm"},null,8,["modelValue","options"])):m("",!0),x(P(nt),{class:"render-error-scroll",style:{width:"100%",height:"420px"}},{default:S(()=>[x(lt,{text:h.value,"highlight-line":e.detail.line??void 0},null,8,["text","highlight-line"])]),_:1})])):(r(),v(P(ee),{key:1,severity:"warn",closable:!1},{default:S(()=>{var O;return[K(g(((O=e.detail)==null?void 0:O.message)||P(n)("proxy.renderErrorNoDetail")),1)]}),_:1}))]),_:1},8,["visible","header"]))}}),ei=Ge(jt,[["__scopeId","data-v-79363ecd"]]);function Gt(e){return e.blocked_by??[]}function Nt(e){return Gt(e).length>0?!0:e.enable===!0&&e.effective_enable===!1}function ti(e){return!!e.enable&&!Nt(e)}function ii(e){const t=e==null?void 0:e.response;if((t==null?void 0:t.status)!==409)return null;const i=t.data??{},n=i.extra_data??{},s=n.blocked_by??i.blocked_by;return s!=null&&s.length?{blocked_by:s,settings_url:n.settings_url??i.settings_url}:null}function ni(){const e=Ne(),{t}=oe();function i(n,s){const l=n.map(a=>a.label).join(", ");e.require({message:t("proxy.needGlobalEnable",{names:l}),header:t("proxy.cannotEnable"),icon:"pi pi-exclamation-triangle",rejectProps:{label:t("common.cancel"),severity:"secondary",outlined:!0},acceptProps:{label:t("proxy.goToSettings")},accept:()=>{s&&window.open(s,"_blank","noopener,noreferrer")}})}return{promptParentEnable:i}}export{ei as R,_t as a,kt as b,Nt as c,Zt as d,Gt as e,Xt as f,ti as i,ii as p,Qt as s,ni as u};
