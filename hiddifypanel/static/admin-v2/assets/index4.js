import{B as l,s as u,f as g,o as s,c as i,q as p,a,af as y,e as c,r as f,i as b,d as m}from"./index.js";var v=`
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
`,k={root:function(t){var e=t.props;return["p-tag p-component",{"p-tag-info":e.severity==="info","p-tag-success":e.severity==="success","p-tag-warn":e.severity==="warn","p-tag-danger":e.severity==="danger","p-tag-secondary":e.severity==="secondary","p-tag-contrast":e.severity==="contrast","p-tag-rounded":e.rounded}]},icon:"p-tag-icon",label:"p-tag-label"},h=l.extend({name:"tag",style:v,classes:k}),S={name:"BaseTag",extends:u,props:{value:null,severity:null,rounded:Boolean,icon:String},style:h,provide:function(){return{$pcTag:this,$parentInstance:this}}};function r(n){"@babel/helpers - typeof";return r=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},r(n)}function w(n,t,e){return(t=$(t))in n?Object.defineProperty(n,t,{value:e,enumerable:!0,configurable:!0,writable:!0}):n[t]=e,n}function $(n){var t=P(n,"string");return r(t)=="symbol"?t:t+""}function P(n,t){if(r(n)!="object"||!n)return n;var e=n[Symbol.toPrimitive];if(e!==void 0){var o=e.call(n,t);if(r(o)!="object")return o;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(n)}var B={name:"Tag",extends:S,inheritAttrs:!1,computed:{dataP:function(){return g(w({rounded:this.rounded},this.severity,this.severity))}}},z=["data-p"];function T(n,t,e,o,j,d){return s(),i("span",a({class:n.cx("root"),"data-p":d.dataP},n.ptmi("root")),[n.$slots.icon?(s(),p(y(n.$slots.icon),a({key:0,class:n.cx("icon")},n.ptm("icon")),null,16,["class"])):n.icon?(s(),i("span",a({key:1,class:[n.cx("icon"),n.icon]},n.ptm("icon")),null,16)):c("",!0),n.value!=null||n.$slots.default?f(n.$slots,"default",{key:2},function(){return[b("span",a({class:n.cx("label")},n.ptm("label")),m(n.value),17)]}):c("",!0)],16,z)}B.render=T;export{B as s};
