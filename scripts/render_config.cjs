// Run inside LibreChat before startup. Keep credentials as environment references.
const fs = require('node:fs');
const yaml = require('js-yaml');
const { configSchema } = require('librechat-data-provider');

for (const name of ['CREATEAI_MODEL', 'CREATEAI_BASE_URL', 'CREATEAI_API_KEY']) {
  if (!process.env[name] || /REPLACE|replace-with/.test(process.env[name])) {
    throw new Error('Set ' + name + ' in .env before starting LibreChat.');
  }
}
if (process.env.ALLOW_PASSWORD_RESET === 'true' &&
    (!process.env.EMAIL_HOST || !process.env.EMAIL_FROM)) {
  throw new Error('Password reset requires EMAIL_HOST and EMAIL_FROM.');
}
const config = yaml.load(fs.readFileSync('/app/config/course-librechat.yaml', 'utf8'));
config.endpoints.custom[0].models.default = [process.env.CREATEAI_MODEL];
for (const spec of config.modelSpecs.list) {
  spec.preset.model = process.env.CREATEAI_MODEL;
}
configSchema.strict().parse(config);
fs.writeFileSync('/app/librechat.yaml', yaml.dump(config));
console.log('Course configuration validated and rendered.');