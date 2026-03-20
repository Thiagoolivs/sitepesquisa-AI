import { Router, type IRouter } from "express";
import healthRouter from "./health.js";
import analisarRouter from "./analisar.js";
import uploadRouter from "./upload.js";
import iaRouter from "./ia.js";
import formularioRouter from "./formulario.js";

const router: IRouter = Router();

router.use(healthRouter);
router.use(analisarRouter);
router.use(uploadRouter);
router.use(iaRouter);
router.use(formularioRouter);

export default router;
