import test from 'node:test';
import assert from 'node:assert/strict';
import { localRequest, createLauncher } from '../index.mjs';

const request = (ip,headers={}) => ({socket:{remoteAddress:ip},headers:{host:'127.0.0.1:8000',...headers}});
test('accepts loopback same-origin requests',()=>{
  assert.equal(localRequest(request('127.0.0.1',{origin:'http://127.0.0.1:8000'})),true);
  assert.equal(localRequest(request('::ffff:127.0.0.1')),true);
});
test('rejects non-local callers, foreign origins and DNS rebinding hosts',()=>{
  assert.equal(localRequest(request('192.168.1.12')),false);
  assert.equal(localRequest(request('127.0.0.1',{origin:'https://evil.example'})),false);
  assert.equal(localRequest(request('127.0.0.1',{host:'evil.example'})),false);
  assert.equal(localRequest(request('127.0.0.1',{'sec-fetch-site':'cross-site'})),false);
});
test('missing menu fails without spawning or retaining a running state',async()=>{
  const launcher=createLauncher('python','a-directory-that-does-not-exist');
  await assert.rejects(launcher.open(),/找不到样式菜单/);
  assert.equal(launcher.running(),false);launcher.dispose();
});
