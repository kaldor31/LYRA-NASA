// Writes the deck's own theme colors and theme name into ppt/theme/theme1.xml after pptxgenjs
// has written the file (pptxgenjs sets the fonts but keeps Office's default palette).
// Also fixes <c:crossesAt val="autoZero"/>, which pptxgenjs writes and PowerPoint repairs,
// and drops folder entries from the ZIP.
const fs = require('fs');
const JSZip = require(require.resolve('jszip', { paths: [require.resolve('pptxgenjs')] }));

const SLOTS = ['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink'];

async function applyTheme(deckPath, theme) {
  for (const k of SLOTS) {
    if (!/^[0-9A-Fa-f]{6}$/.test(String(theme.colors[k]))) throw new Error(`theme.colors.${k} must be six hex digits`);
  }
  const name = String(theme.name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const zip = await JSZip.loadAsync(fs.readFileSync(deckPath));
  const part = 'ppt/theme/theme1.xml';
  const scheme = `<a:clrScheme name="${name}">` + SLOTS.map(k => `<a:${k}><a:srgbClr val="${theme.colors[k].toUpperCase()}"/></a:${k}>`).join('') + '</a:clrScheme>';
  const xml = (await zip.file(part).async('string'))
    .replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, () => scheme)
    .replace(/(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"/g, (_, head) => `${head}${name}"`);
  zip.file(part, xml);
  for (const n of Object.keys(zip.files)) {
    if (zip.files[n].dir || !n.endsWith('.xml')) continue;
    const x = await zip.file(n).async('string');
    const bad = x.match(/<a:srgbClr val="((?![0-9A-Fa-f]{6}")[^"]*)"/);
    if (bad) throw new Error(`${n}: <a:srgbClr val="${bad[1]}"> is not a hex color (scheme color passed to a hex-only option)`);
    if (x.includes('<c:crossesAt val="autoZero"/>')) zip.file(n, x.replaceAll('<c:crossesAt val="autoZero"/>', '<c:crosses val="autoZero"/>'));
  }
  for (const n of Object.keys(zip.files)) if (zip.files[n].dir) delete zip.files[n];
  fs.writeFileSync(deckPath, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}

module.exports = { applyTheme };
