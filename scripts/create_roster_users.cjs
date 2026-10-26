// Run inside LibreChat with one roster email per line on stdin.
// Creates accounts only; does not send email or display generated passwords.
const path = require('node:path');
const fs = require('node:fs');
const { randomBytes } = require('node:crypto');
const mongoose = require('mongoose');
require('module-alias')({ base: path.resolve(__dirname, '..', 'api') });
const { User } = require('@librechat/data-schemas').createModels(mongoose);
const { registerUser } = require('~/server/services/AuthService');
const connect = require('./connect');

(async () => {
  const emails = [...new Set(fs.readFileSync(0, 'utf8').split(/\r?\n/)
    .map(line => line.trim().toLowerCase()).filter(line => line && !line.startsWith('#')))];
  if (emails.some(email => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) {
    throw new Error('Use one valid email address per line; no CSV header or names.');
  }
  await connect();
  if (await User.countDocuments() === 0) {
    throw new Error('Create the instructor administrator account first.');
  }
  for (const email of emails) {
    if (await User.findOne({ email })) {
      console.log('Already exists: ' + email);
      continue;
    }
    const password = randomBytes(32).toString('hex');
    const result = await registerUser({
      email, name: email.split('@')[0],
      username: 'student_' + randomBytes(8).toString('hex'),
      password, confirm_password: password,
    }, { emailVerified: true });
    if (result.status !== 200) throw new Error(email + ': ' + result.message);
    console.log('Created: ' + email);
  }
  await mongoose.disconnect();
  process.exit(0);
})().catch(error => {
  console.error(error.message);
  process.exit(1);
});