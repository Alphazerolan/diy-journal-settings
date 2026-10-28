// The build embeds the same reviewed mapping used by the Python editor.
export function adaptJournalCSS(css, profile, modules) {
  if (profile !== 'rc3') return css;
  const token = /:is\(\.[\w-]+,\.[\w-]+\)|\.([_a-zA-Z0-9-]{6,7})_([a-zA-Z][\w-]*)/g;
  return css.replace(token, (whole, prefix, suffix) => {
    if (whole.startsWith(':is(')) {
      const pair = whole.slice(4, -1).split(',');
      const left = /^\.([_a-zA-Z0-9-]{6,7})_([a-zA-Z][\w-]*)$/.exec(pair[0]);
      if (left && pair[1] === '.' + modules[left[1]] + '_' + left[2]) return whole;
      return ':is(' + pair.map(item => adaptJournalCSS(item, profile, modules)).join(',') + ')';
    }
    return modules[prefix] ? ':is(.' + prefix + '_' + suffix + ',.' + modules[prefix] + '_' + suffix + ')' : whole;
  });
}
