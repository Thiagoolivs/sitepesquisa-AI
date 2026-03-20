import { Router, type IRouter } from "express";
import healthRouter from "./health";
import analisarRouter from "./analisar";

const router: IRouter = Router();

router.use(healthRouter);
router.use(analisarRouter);

export default router;
