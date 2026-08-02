// Example Playwright spec for the taskboard app. This is what
// `democreator discover examples/taskboard/tests` parses into draft flows.
import { test, expect } from '@playwright/test';

test('add and complete a task @smoke', async ({ page }) => {
  await page.goto('http://localhost:8123/');
  await page.fill('#new-task', 'Write the quarterly report');
  await page.getByRole('button', { name: 'Add task' }).click();
  await expect(page.locator('#tasks li')).toBeVisible();
  await page.locator('#tasks li input[type=checkbox]').check();
});

test('filter to done tasks', async ({ page }) => {
  await page.goto('http://localhost:8123/');
  await page.fill('#new-task', 'Ship the release');
  await page.getByRole('button', { name: 'Add task' }).click();
  await page.locator('#tasks li input[type=checkbox]').check();
  await page.getByRole('button', { name: 'Done' }).click();
  await expect(page.locator('#tasks li.done')).toBeVisible();
});
