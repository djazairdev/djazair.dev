/* Anonymous action counts. No identifiers, raw URLs, titles or user-generated text. */
(function () {
 'use strict';
 var path=location.pathname.split('/'), language=path[1], page=path[2] || 'home';
 if (!['en','ar'].includes(language)) return;
 var trackedPage=['home','hub','meetups'].includes(page);
 var privateMode=navigator.doNotTrack==='1' || navigator.globalPrivacyControl===true;
 var query=new URLSearchParams(location.search), campaign={};
 ['source','medium','campaign'].forEach(function (key) {
   var value=query.get('utm_'+key) || '';
   campaign[key]=/^[a-z0-9_-]{1,64}$/.test(value) ? value : 'none';
 });
 if (campaign.source==='none') {
   var host=''; try { host=new URL(document.referrer).hostname; } catch (_) {}
   if (/(^|\.)(facebook\.com|instagram\.com|t\.co|x\.com|twitter\.com)$/.test(host)) campaign.source='social';
   else if (/(^|\.)(google\.com|bing\.com)$/.test(host)) campaign.source='search';
   else campaign.source=host && host!==location.hostname ? 'external' : 'direct';
 }
 var sent=0;
 function emit(event,section) {
   if (privateMode || !trackedPage || sent>=50) return;
   sent++;
   var payload=JSON.stringify({event:event,page:page,language:language,section:section || 'other',
     source:campaign.source,medium:campaign.medium,campaign:campaign.campaign});
   fetch('/api/events',{method:'POST',headers:{'Content-Type':'application/json'},body:payload,
     keepalive:true,credentials:'omit',cache:'no-store'}).catch(function () {});
 }
 // Keep only campaign codes across the Hub and the city meetup platform. Never add click IDs.
 function attributed(url) {
   if (privateMode || campaign.source==='direct' && campaign.medium==='none' && campaign.campaign==='none') return url;
   ['source','medium','campaign'].forEach(function (key) {
     if (campaign[key]!=='none' && !url.searchParams.has('utm_'+key)) url.searchParams.set('utm_'+key,campaign[key]);
   });
   return url;
 }
 document.querySelectorAll('a[href]').forEach(function (link) {
   if ((link.getAttribute('href') || '').startsWith('#')) return;
   var url; try { url=new URL(link.href); } catch (_) { return; }
   if (url.origin===location.origin || url.hostname==='founders.coffee') {
     if (url.origin===location.origin && !/^\/(en|ar)\/(?:[a-z-]+\/)*$/.test(url.pathname)) return;
     if (url.hostname==='founders.coffee' && !/^\/(en|ar)\/algeria(?:\/|$)/.test(url.pathname)) return;
     link.href=attributed(url).href;
   }
 });
 var latestClick=0;
 document.addEventListener('click',function (e) {
   var link=e.target.closest('a[href]'); if (!link) return;
   var url; try { url=new URL(link.href); } catch (_) { return; }
   var event='';
   if (url.origin===location.origin && /^\/(en|ar)\/hub\/$/.test(url.pathname)) event='task_browse';
   if (url.hostname==='github.com' && /^\/[^/]+\/[^/]+\/issues\/\d+$/.test(url.pathname)) event='task_open';
   if (url.hostname==='founders.coffee' && /^\/(en|ar)\/algeria(?:\/|$)/.test(url.pathname)) {
     event=/\/new(?:\/|$)|\/host(?:\/|$)/.test(url.pathname) ? 'meetup_host' : 'meetup_find';
   }
   if (!event || Date.now()-latestClick<400) return;
   latestClick=Date.now();
   var section=link.closest('section'), id=section && section.id;
   emit(event,section && section.classList.contains('hero') ? 'hero' :
     ['contribution-start','local-team','hub-teaser'].includes(id) ? id : 'other');
 });
 var share=document.querySelector('[data-community-share]');
 if (share && (navigator.share || navigator.clipboard && window.isSecureContext)) {
   share.parentElement.hidden=false;
   share.addEventListener('click',async function () {
     var status=share.parentElement.querySelector('[role=status]');
     // Shared links get their own channel; original ads are never attributed to recipients.
     var url='https://djazair.dev/'+language+'/?utm_source=community&utm_medium=share&utm_campaign=city-builders';
     share.disabled=true;
     try {
       if (navigator.share) {
         emit('share_open','contribution-start');
         await navigator.share({title:'djazair.dev',url:url});
         emit('share_complete','contribution-start');
       } else {
         await navigator.clipboard.writeText(url);
         status.textContent=share.dataset.copied;
         emit('share_copy','contribution-start');
       }
     } catch (err) { if (err.name!=='AbortError') status.textContent=share.dataset.failed; }
     finally { share.disabled=false; }
   });
 }
 if (trackedPage) emit(page==='home' ? 'landing_view' : page+'_view');
})();
