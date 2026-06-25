import { createRouter, createWebHistory } from 'vue-router'
import RunView from '../views/RunView.vue'
import CCGMASView from '../views/CCGMASView.vue'
import GlossaryView from '../views/GlossaryView.vue'
import DatasetManageView from '../views/DatasetManageView.vue'

const routes = [
  { path: '/', redirect: '/run' },
  { path: '/run', component: RunView },
  { path: '/ccgmas', component: CCGMASView },
  { path: '/datasets', component: DatasetManageView },
  { path: '/glossary', component: GlossaryView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
